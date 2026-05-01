import Foundation

@MainActor
final class SyncManager {
    private let apiClient: ApiClient
    private let healthKitService: HealthKitService

    init(apiClient: ApiClient = .shared, healthKitService: HealthKitService = HealthKitService()) {
        self.apiClient = apiClient
        self.healthKitService = healthKitService
    }

    func ensureDeviceAuth(currentToken: String?) async throws -> String {
        if let token = currentToken, token.isEmpty == false {
            return token
        }
        let auth = try await apiClient.authenticateDevice()
        return auth.apiToken
    }

    func syncToday(apiToken: String) async throws -> Date {
        let payload = await healthKitService.dailyPayload()
        try await apiClient.sendDailyMetrics(payload: payload, apiToken: apiToken)
        return Date()
    }

    func generateLinkCode(apiToken: String) async throws -> LinkCodeResponse {
        try await apiClient.createLinkCode(apiToken: apiToken)
    }

    func requestHealthAccess() async throws {
        try await healthKitService.requestAuthorization()
    }

    func healthKitHasCompletedAuthorizationPrompt() async throws -> Bool {
        try await healthKitService.hasCompletedAuthorizationPrompt()
    }

    func fetchWeeklyActivity(days: Int) async -> [WeeklyActivityPoint] {
        await healthKitService.weeklyActivity(days: days)
    }

    func startHealthBackgroundUpdates(onChange: @escaping @Sendable () -> Void) async {
        await healthKitService.startBackgroundDelivery(onChange: onChange)
    }
}
