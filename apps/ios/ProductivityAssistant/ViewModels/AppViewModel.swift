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
    @Published var weeklyActivity: [WeeklyActivityPoint] = []
    @Published var weeklyActivityRangeDays = 7
    @Published var userProfile: UserProfileDTO?
    @Published var dailyInsightText: String = ""
    @Published var weeklyInsightText: String = ""

    let syncManager = SyncManager()
    private var autoSyncStarted = false

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
        await fetchDailyInsightPreview()
    }

    func performBackgroundSync() async {
        do {
            let token = try await ensureToken()
            let syncedAt = try await syncManager.syncToday(apiToken: token)
            lastSyncAt = syncedAt
            UserDefaults.standard.set(syncedAt, forKey: "last_sync_at")
            try await refreshStatusInternal(apiToken: token)
        } catch {
            // Keep background sync best-effort; foreground screens will surface errors.
        }
    }

    func autoSyncIfStale(maxAgeMinutes: Int = 20) async {
        if isLoading {
            return
        }
        let threshold = Date().addingTimeInterval(TimeInterval(-max(1, maxAgeMinutes) * 60))
        if let lastSyncAt, lastSyncAt > threshold {
            return
        }
        await performBackgroundSync()
    }

    func startAutomaticHealthSync() async {
        if autoSyncStarted {
            return
        }
        autoSyncStarted = true
        do {
            try await syncManager.startHealthBackgroundUpdates { [weak self] in
                guard let self else { return }
                Task { @MainActor in
                    await self.performBackgroundSync()
                }
            }
        } catch {
            // Keep app functional even if HealthKit background observers fail.
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
        await fetchDailyInsightPreview()
    }

    func fetchWeeklyActivity() async {
        await run {
            weeklyActivity = try await syncManager.fetchWeeklyActivity(days: weeklyActivityRangeDays)
        }
    }

    func loadUserProfile() async {
        await run {
            let token = try await ensureToken()
            userProfile = try await ApiClient.shared.getUserProfile(apiToken: token)
        }
    }

    func saveUserProfile(patch: UserProfilePatch) async {
        await run {
            let token = try await ensureToken()
            userProfile = try await ApiClient.shared.patchUserProfile(apiToken: token, patch: patch)
        }
    }

    func postUserWeight(weightKg: Double) async {
        await run {
            let token = try await ensureToken()
            userProfile = try await ApiClient.shared.postProfileWeight(apiToken: token, weightKg: weightKg)
        }
    }

    /// Logs subjective stress/fatigue for the user's current local calendar day.
    func postTodaySubjective(stress: Int, fatigue: Int, note: String?) async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }
        do {
            let token = try await ensureToken()
            let dateStr = AppViewModel.isoDateLocal(Date())
            let payload = SubjectiveDailyPayload(
                date: dateStr,
                stress: stress,
                fatigue: fatigue,
                note: note
            )
            _ = try await ApiClient.shared.postProfileSubjective(apiToken: token, payload: payload)
        } catch {
            errorMessage = mapErrorMessage(error)
        }
    }

    private static func isoDateLocal(_ date: Date) -> String {
        let f = DateFormatter()
        f.calendar = Calendar(identifier: .gregorian)
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone.current
        f.dateFormat = "yyyy-MM-dd"
        return f.string(from: date)
    }

    func fetchInsights() async {
        await run {
            let token = try await ensureToken()
            async let daily = ApiClient.shared.getDailyInsights(apiToken: token)
            async let weekly = ApiClient.shared.getWeeklyInsights(apiToken: token)
            let (d, w) = try await (daily, weekly)
            dailyInsightText = d.text
            weeklyInsightText = w.text
        }
    }

    /// Dashboard preview: daily insight only. Does not toggle `isLoading` or set `errorMessage` so it never masks sync/status errors.
    func fetchDailyInsightPreview() async {
        do {
            let token = try await ensureToken()
            let d = try await ApiClient.shared.getDailyInsights(apiToken: token)
            dailyInsightText = d.text
        } catch {
            // Keep prior text on failure; first-load empty shows placeholder in UI.
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
            errorMessage = mapErrorMessage(error)
        }
        isLoading = false
    }

    private func mapErrorMessage(_ error: Error) -> String {
        if let urlError = error as? URLError {
            switch urlError.code {
            case .notConnectedToInternet, .networkConnectionLost, .cannotConnectToHost:
                return String(localized: "error.network_offline")
            case .timedOut:
                return String(localized: "error.request_timeout")
            default:
                return String(localized: "error.generic")
            }
        }

        let nsError = error as NSError
        if nsError.domain == "ApiClient" {
            if nsError.code == 401 {
                return String(localized: "error.auth_invalid")
            }
            if nsError.code >= 500 {
                return String(localized: "error.server_unavailable")
            }
        }
        return String(localized: "error.generic")
    }
}
