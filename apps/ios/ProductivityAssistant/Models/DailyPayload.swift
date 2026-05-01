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

struct MedicalFlagsDTO: Codable {
    let chronicCondition: Bool
    let pregnancy: Bool
    let takesMedications: Bool

    enum CodingKeys: String, CodingKey {
        case chronicCondition = "chronic_condition"
        case pregnancy
        case takesMedications = "takes_medications"
    }

    static let empty = MedicalFlagsDTO(chronicCondition: false, pregnancy: false, takesMedications: false)
}

struct UserProfileDTO: Codable {
    let heightCm: Int?
    let sex: String?
    let birthYear: Int?
    let goalType: String?
    let goalTargetWeightKg: Double?
    let goalHorizonDate: String?
    let dietNotes: String?
    let medicalFlags: MedicalFlagsDTO
    let quietHoursStart: String?
    let quietHoursEnd: String?
    let weeklyWeighInWeekday: Int?
    let lastWeightKg: Double?
    let lastWeightAt: String?
    let maxAlertsPerDay: Int
    let foodLoggingEnabled: Bool
}

struct InsightTextResponse: Codable {
    let text: String
    let date: String?
    let weekEnd: String?

    enum CodingKeys: String, CodingKey {
        case text
        case date
        case weekEnd = "week_end"
    }
}

struct WeightIngestPayload: Encodable {
    let weightKg: Double
}

/// POST /v1/profile/subjective — keys must match API (`stress_0_5`, `fatigue_0_5`).
struct SubjectiveDailyPayload: Encodable {
    let date: String
    let stress: Int
    let fatigue: Int
    var note: String?

    enum CodingKeys: String, CodingKey {
        case date
        case stress = "stress_0_5"
        case fatigue = "fatigue_0_5"
        case note
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(date, forKey: .date)
        try c.encode(stress, forKey: .stress)
        try c.encode(fatigue, forKey: .fatigue)
        let trimmed = note?.trimmingCharacters(in: .whitespacesAndNewlines)
        if let trimmed, !trimmed.isEmpty {
            try c.encode(trimmed, forKey: .note)
        }
    }
}

struct SubjectiveSaveResponse: Codable {
    let status: String
    let date: String
}

struct UserProfilePatch: Encodable {
    var heightCm: Int?
    var goalType: String?
    var dietNotes: String?
    var foodLoggingEnabled: Bool?
    var maxAlertsPerDay: Int?

    enum CodingKeys: String, CodingKey {
        case heightCm
        case goalType
        case dietNotes
        case foodLoggingEnabled
        case maxAlertsPerDay
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        if let heightCm { try c.encode(heightCm, forKey: .heightCm) }
        if let goalType { try c.encode(goalType, forKey: .goalType) }
        if let dietNotes { try c.encode(dietNotes, forKey: .dietNotes) }
        if let foodLoggingEnabled { try c.encode(foodLoggingEnabled, forKey: .foodLoggingEnabled) }
        if let maxAlertsPerDay { try c.encode(maxAlertsPerDay, forKey: .maxAlertsPerDay) }
    }
}
