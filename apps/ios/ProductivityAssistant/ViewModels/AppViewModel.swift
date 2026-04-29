import Foundation

@MainActor
final class AppViewModel: ObservableObject {
    @Published var apiToken: String = UserDefaults.standard.string(forKey: "api_token") ?? ""
    @Published var lastSyncAt: Date? = UserDefaults.standard.object(forKey: "last_sync_at") as? Date
    @Published var linkCode: String = ""
    @Published var healthAccessGranted = false
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var todayReport: String = ""
    @Published var weekReport: String = ""
    @Published var isLinked = false
    @Published var profileLanguage = "ru"
    @Published var profileTimezone = "Asia/Baku"
    @Published var lastSyncDateFromServer: String?
    @Published var hasTodayScore = false

    let syncManager = SyncManager()

    func requestHealthAccess() async {
        await run {
            try await syncManager.requestHealthAccess()
            healthAccessGranted = true
        }
    }

    func syncNow() async {
        await run {
            let token = try await ensureToken()
            let syncedAt = try await syncManager.syncToday(apiToken: token)
            lastSyncAt = syncedAt
            UserDefaults.standard.set(syncedAt, forKey: "last_sync_at")
            try await refreshStatusInternal(apiToken: token)
            if hasTodayScore {
                let response = try await ApiClient.shared.getTodayReport(apiToken: token)
                todayReport = response.report
            }
        }
    }

    func fetchLinkCode() async {
        await run {
            let token = try await ensureToken()
            let codeResponse = try await syncManager.generateLinkCode(apiToken: token)
            linkCode = codeResponse.code
        }
    }

    func fetchTodayReport() async {
        await run {
            let token = try await ensureToken()
            let response = try await ApiClient.shared.getTodayReport(apiToken: token)
            todayReport = response.report
        }
    }

    func fetchWeekReport() async {
        await run {
            let token = try await ensureToken()
            let response = try await ApiClient.shared.getWeekReport(apiToken: token)
            weekReport = response.report
        }
    }

    func refreshReportStatus() async {
        await run {
            let token = try await ensureToken()
            try await refreshStatusInternal(apiToken: token)
        }
    }

    private func persistToken(_ token: String) {
        apiToken = token
        UserDefaults.standard.set(token, forKey: "api_token")
    }

    private func ensureToken() async throws -> String {
        let token = try await syncManager.ensureDeviceAuth(currentToken: apiToken)
        persistToken(token)
        return token
    }

    private func refreshStatusInternal(apiToken: String) async throws {
        let status = try await ApiClient.shared.getReportStatus(apiToken: apiToken)
        isLinked = status.isLinked
        profileLanguage = status.language
        profileTimezone = status.timezone
        lastSyncDateFromServer = status.lastSyncDate
        hasTodayScore = status.hasTodayScore
    }

    private func run(_ operation: () async throws -> Void) async {
        isLoading = true
        errorMessage = nil
        do {
            try await operation()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}
