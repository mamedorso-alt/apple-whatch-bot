import Foundation
import HealthKit

final class HealthKitService {
    private let store = HKHealthStore()
    private var observerQueries: [HKObserverQuery] = []
    private var onBackgroundChange: (@Sendable () -> Void)?

    private var readTypes: Set<HKObjectType> {
        var types = Set<HKObjectType>()
        let quantityTypes: [HKQuantityTypeIdentifier] = [
            .stepCount,
            .activeEnergyBurned,
            .heartRate,
            .restingHeartRate,
            .heartRateVariabilitySDNN,
        ]
        quantityTypes.forEach { id in
            if let quantityType = HKObjectType.quantityType(forIdentifier: id) {
                types.insert(quantityType)
            }
        }
        if let sleep = HKObjectType.categoryType(forIdentifier: .sleepAnalysis) {
            types.insert(sleep)
        }
        if let workout = HKObjectType.workoutType() as HKObjectType? {
            types.insert(workout)
        }
        return types
    }

    func requestAuthorization() async throws {
        guard HKHealthStore.isHealthDataAvailable() else {
            throw NSError(domain: "HealthKitService", code: 1, userInfo: [NSLocalizedDescriptionKey: "Health data is unavailable"])
        }
        try await store.requestAuthorization(toShare: [], read: readTypes)
    }

    func startBackgroundDelivery(onChange: @escaping @Sendable () -> Void) async throws {
        guard HKHealthStore.isHealthDataAvailable() else {
            return
        }
        onBackgroundChange = onChange
        stopBackgroundDelivery()

        for objectType in readTypes {
            guard let sampleType = objectType as? HKSampleType else { continue }
            let query = HKObserverQuery(sampleType: sampleType, predicate: nil) { [weak self] _, completionHandler, _ in
                if let callback = self?.onBackgroundChange {
                    callback()
                }
                completionHandler()
            }
            observerQueries.append(query)
            store.execute(query)
            try await store.enableBackgroundDelivery(for: sampleType, frequency: .immediate)
        }
    }

    func stopBackgroundDelivery() {
        for query in observerQueries {
            store.stop(query)
        }
        observerQueries.removeAll()
    }

    func dailyPayload(for day: Date = Date(), timezone: TimeZone = .current) async throws -> DailyPayload {
        let calendar = Calendar.current
        let startOfDay = calendar.startOfDay(for: day)
        let endOfDay = calendar.date(byAdding: .day, value: 1, to: startOfDay) ?? day

        async let steps = sumQuantity(.stepCount, unit: HKUnit.count(), start: startOfDay, end: endOfDay)
        async let activeKcal = sumQuantity(.activeEnergyBurned, unit: .kilocalorie(), start: startOfDay, end: endOfDay)
        async let sleepData = sleepDuration(start: startOfDay, end: endOfDay)
        async let restingHR = averageQuantity(.restingHeartRate, unit: HKUnit.count().unitDivided(by: .minute()), start: startOfDay, end: endOfDay)
        async let hrv = averageQuantity(.heartRateVariabilitySDNN, unit: HKUnit.secondUnit(with: .milli), start: startOfDay, end: endOfDay)
        async let workouts = workoutsCount(start: startOfDay, end: endOfDay)

        let sleep = try await sleepData
        let dateString = isoDate(startOfDay)

        return DailyPayload(
            date: dateString,
            timezone: timezone.identifier,
            steps: Int(try await steps),
            activeKcal: try await activeKcal,
            sleepMin: Int(sleep.minutes),
            sleepStart: sleep.start.map(isoDateTime),
            sleepEnd: sleep.end.map(isoDateTime),
            restingHr: try await restingHR,
            hrvSdnn: try await hrv,
            workoutsCount: try await workouts
        )
    }

    func weeklyActivity(days: Int = 7, endingAt day: Date = Date(), timezone: TimeZone = .current) async throws -> [WeeklyActivityPoint] {
        let safeDays = max(1, days)
        let calendar = Calendar.current
        let endDayStart = calendar.startOfDay(for: day)
        _ = timezone

        var points: [WeeklyActivityPoint] = []
        for offset in stride(from: safeDays - 1, through: 0, by: -1) {
            guard let currentDay = calendar.date(byAdding: .day, value: -offset, to: endDayStart),
                  let nextDay = calendar.date(byAdding: .day, value: 1, to: currentDay) else {
                continue
            }

            let steps = try await sumQuantity(.stepCount, unit: HKUnit.count(), start: currentDay, end: nextDay)
            let kcal = try await sumQuantity(.activeEnergyBurned, unit: .kilocalorie(), start: currentDay, end: nextDay)
            points.append(
                WeeklyActivityPoint(
                    date: currentDay,
                    steps: steps,
                    activeKcal: kcal
                )
            )
        }
        return points
    }

    private func sumQuantity(_ id: HKQuantityTypeIdentifier, unit: HKUnit, start: Date, end: Date) async throws -> Double {
        guard let type = HKObjectType.quantityType(forIdentifier: id) else { return 0 }
        return try await withCheckedThrowingContinuation { continuation in
            let predicate = HKQuery.predicateForSamples(withStart: start, end: end, options: .strictStartDate)
            let query = HKStatisticsQuery(quantityType: type, quantitySamplePredicate: predicate, options: .cumulativeSum) { _, result, error in
                if let error {
                    continuation.resume(throwing: error)
                    return
                }
                let value = result?.sumQuantity()?.doubleValue(for: unit) ?? 0
                continuation.resume(returning: value)
            }
            self.store.execute(query)
        }
    }

    private func averageQuantity(_ id: HKQuantityTypeIdentifier, unit: HKUnit, start: Date, end: Date) async throws -> Double? {
        guard let type = HKObjectType.quantityType(forIdentifier: id) else { return nil }
        return try await withCheckedThrowingContinuation { continuation in
            let predicate = HKQuery.predicateForSamples(withStart: start, end: end, options: .strictStartDate)
            let query = HKStatisticsQuery(quantityType: type, quantitySamplePredicate: predicate, options: .discreteAverage) { _, result, error in
                if let error {
                    continuation.resume(throwing: error)
                    return
                }
                let value = result?.averageQuantity()?.doubleValue(for: unit)
                continuation.resume(returning: value)
            }
            self.store.execute(query)
        }
    }

    private func workoutsCount(start: Date, end: Date) async throws -> Int {
        try await withCheckedThrowingContinuation { continuation in
            let predicate = HKQuery.predicateForSamples(withStart: start, end: end, options: .strictStartDate)
            let query = HKSampleQuery(sampleType: .workoutType(), predicate: predicate, limit: HKObjectQueryNoLimit, sortDescriptors: nil) { _, samples, error in
                if let error {
                    continuation.resume(throwing: error)
                    return
                }
                continuation.resume(returning: samples?.count ?? 0)
            }
            self.store.execute(query)
        }
    }

    /// Raw values for time actually asleep (Apple Watch uses stage samples, not legacy `.asleep` only).
    private static let asleepStageRawValues: Set<Int> = [
        HKCategoryValueSleepAnalysis.asleep.rawValue,
        HKCategoryValueSleepAnalysis.asleepUnspecified.rawValue,
        HKCategoryValueSleepAnalysis.asleepCore.rawValue,
        HKCategoryValueSleepAnalysis.asleepDeep.rawValue,
        HKCategoryValueSleepAnalysis.asleepREM.rawValue,
    ]

    /// Sleep attributed to calendar `day`: main night is usually recorded starting the evening before.
    /// We fetch a wide window, cluster asleep segments into sessions, and pick sessions whose end falls on this day (wake-up day).
    private func sleepDuration(start: Date, end: Date) async throws -> (minutes: Double, start: Date?, end: Date?) {
        guard let sleepType = HKObjectType.categoryType(forIdentifier: .sleepAnalysis) else {
            return (0, nil, nil)
        }
        let calendar = Calendar.current
        guard let queryStart = calendar.date(byAdding: .hour, value: -18, to: start),
              let queryEnd = calendar.date(byAdding: .hour, value: 12, to: end) else {
            return (0, nil, nil)
        }

        return try await withCheckedThrowingContinuation { continuation in
            let predicate = HKQuery.predicateForSamples(withStart: queryStart, end: queryEnd, options: [])
            let query = HKSampleQuery(sampleType: sleepType, predicate: predicate, limit: HKObjectQueryNoLimit, sortDescriptors: nil) { _, samples, error in
                if let error {
                    continuation.resume(throwing: error)
                    return
                }
                let entries = (samples as? [HKCategorySample]) ?? []
                let asleepSamples = entries.filter { Self.asleepStageRawValues.contains($0.value) }

                let gapBreakSeconds: TimeInterval = 2 * 3600
                var totalMinutes = 0.0
                var earliestStart: Date?
                var latestEnd: Date?

                func accumulateSessions(_ samples: [HKCategorySample]) {
                    guard !samples.isEmpty else { return }
                    var clustered: [[HKCategorySample]] = []
                    var cur: [HKCategorySample] = []
                    for sample in samples.sorted(by: { $0.startDate < $1.startDate }) {
                        if let last = cur.last, sample.startDate.timeIntervalSince(last.endDate) > gapBreakSeconds {
                            clustered.append(cur)
                            cur = [sample]
                        } else {
                            cur.append(sample)
                        }
                    }
                    if !cur.isEmpty { clustered.append(cur) }

                    for session in clustered {
                        let sessionEnd = session.map(\.endDate).max() ?? start
                        guard sessionEnd >= start, sessionEnd < end else { continue }

                        for sample in session {
                            totalMinutes += sample.endDate.timeIntervalSince(sample.startDate) / 60.0
                        }
                        let sessionStart = session.map(\.startDate).min()
                        if let sessionStart {
                            earliestStart = min(earliestStart ?? sessionStart, sessionStart)
                        }
                        latestEnd = max(latestEnd ?? sessionEnd, sessionEnd)
                    }
                }

                accumulateSessions(asleepSamples)

                if totalMinutes < 1 {
                    let inBedSamples = entries.filter { $0.value == HKCategoryValueSleepAnalysis.inBed.rawValue }
                    accumulateSessions(inBedSamples)
                }

                continuation.resume(returning: (totalMinutes, earliestStart, latestEnd))
            }
            self.store.execute(query)
        }
    }

    private func isoDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.timeZone = .current
        return formatter.string(from: date)
    }

    private func isoDateTime(_ date: Date) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter.string(from: date)
    }
}
