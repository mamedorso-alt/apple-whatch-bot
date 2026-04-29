import Foundation
import HealthKit

final class HealthKitService {
    private let store = HKHealthStore()

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

    private func sleepDuration(start: Date, end: Date) async throws -> (minutes: Double, start: Date?, end: Date?) {
        guard let sleepType = HKObjectType.categoryType(forIdentifier: .sleepAnalysis) else {
            return (0, nil, nil)
        }
        return try await withCheckedThrowingContinuation { continuation in
            let predicate = HKQuery.predicateForSamples(withStart: start, end: end, options: .strictStartDate)
            let query = HKSampleQuery(sampleType: sleepType, predicate: predicate, limit: HKObjectQueryNoLimit, sortDescriptors: nil) { _, samples, error in
                if let error {
                    continuation.resume(throwing: error)
                    return
                }
                let entries = (samples as? [HKCategorySample]) ?? []
                let filtered = entries.filter { $0.value == HKCategoryValueSleepAnalysis.asleep.rawValue }
                let minutes = filtered.reduce(0.0) { partial, sample in
                    partial + sample.endDate.timeIntervalSince(sample.startDate) / 60.0
                }
                let first = filtered.min(by: { $0.startDate < $1.startDate })?.startDate
                let last = filtered.max(by: { $0.endDate < $1.endDate })?.endDate
                continuation.resume(returning: (minutes, first, last))
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
