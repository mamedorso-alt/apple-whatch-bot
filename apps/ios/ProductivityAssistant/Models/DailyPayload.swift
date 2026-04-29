import Foundation

struct DailyPayload: Codable {
    let date: String
    let timezone: String
    let steps: Int
    let activeKcal: Double
    let sleepMin: Int
    let sleepStart: String?
    let sleepEnd: String?
    let restingHr: Double?
    let hrvSdnn: Double?
    let workoutsCount: Int

    enum CodingKeys: String, CodingKey {
        case date
        case timezone
        case steps
        case activeKcal = "active_kcal"
        case sleepMin = "sleep_min"
        case sleepStart = "sleep_start"
        case sleepEnd = "sleep_end"
        case restingHr = "resting_hr"
        case hrvSdnn = "hrv_sdnn"
        case workoutsCount = "workouts_count"
    }
}

struct DeviceAuthResponse: Codable {
    let userId: UUID
    let apiToken: String

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case apiToken = "api_token"
    }
}

struct LinkCodeResponse: Codable {
    let code: String
    let expiresAt: String

    enum CodingKeys: String, CodingKey {
        case code
        case expiresAt = "expires_at"
    }
}

struct TextReportResponse: Codable {
    let report: String
}

struct ReportStatusResponse: Codable {
    let isLinked: Bool
    let language: String
    let timezone: String
    let lastSyncDate: String?
    let hasTodayScore: Bool

    enum CodingKeys: String, CodingKey {
        case isLinked = "is_linked"
        case language
        case timezone
        case lastSyncDate = "last_sync_date"
        case hasTodayScore = "has_today_score"
    }
}
