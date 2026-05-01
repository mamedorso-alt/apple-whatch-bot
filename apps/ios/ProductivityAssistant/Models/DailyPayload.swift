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

    enum CodingKeys: String, CodingKey {
        case heightCm = "height_cm"
        case sex
        case birthYear = "birth_year"
        case goalType = "goal_type"
        case goalTargetWeightKg = "goal_target_weight_kg"
        case goalHorizonDate = "goal_horizon_date"
        case dietNotes = "diet_notes"
        case medicalFlags = "medical_flags"
        case quietHoursStart = "quiet_hours_start"
        case quietHoursEnd = "quiet_hours_end"
        case weeklyWeighInWeekday = "weekly_weigh_in_weekday"
        case lastWeightKg = "last_weight_kg"
        case lastWeightAt = "last_weight_at"
        case maxAlertsPerDay = "max_alerts_per_day"
        case foodLoggingEnabled = "food_logging_enabled"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        heightCm = try c.decodeIfPresent(Int.self, forKey: .heightCm)
        sex = try c.decodeIfPresent(String.self, forKey: .sex)
        birthYear = try c.decodeIfPresent(Int.self, forKey: .birthYear)
        goalType = try c.decodeIfPresent(String.self, forKey: .goalType)
        goalTargetWeightKg = Self.decodeFlexibleDouble(c, .goalTargetWeightKg)
        goalHorizonDate = try c.decodeIfPresent(String.self, forKey: .goalHorizonDate)
        dietNotes = try c.decodeIfPresent(String.self, forKey: .dietNotes)
        medicalFlags = try c.decodeIfPresent(MedicalFlagsDTO.self, forKey: .medicalFlags) ?? .empty
        quietHoursStart = try c.decodeIfPresent(String.self, forKey: .quietHoursStart)
        quietHoursEnd = try c.decodeIfPresent(String.self, forKey: .quietHoursEnd)
        weeklyWeighInWeekday = try c.decodeIfPresent(Int.self, forKey: .weeklyWeighInWeekday)
        lastWeightKg = Self.decodeFlexibleDouble(c, .lastWeightKg)
        lastWeightAt = try c.decodeIfPresent(String.self, forKey: .lastWeightAt)
        maxAlertsPerDay = try c.decodeIfPresent(Int.self, forKey: .maxAlertsPerDay) ?? 3
        foodLoggingEnabled = try c.decodeIfPresent(Bool.self, forKey: .foodLoggingEnabled) ?? true
    }

    /// Pydantic may send `Decimal` weights as JSON strings; accept both.
    private static func decodeFlexibleDouble(_ c: KeyedDecodingContainer<CodingKeys>, _ key: CodingKeys) -> Double? {
        if let d = try? c.decodeIfPresent(Double.self, forKey: key) { return d }
        if let s = try? c.decodeIfPresent(String.self, forKey: key) { return Double(s) }
        return nil
    }
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

struct AgentSpendResponse: Codable {
    let currency: String
    let dayUsd: Double
    let weekUsd: Double
    let monthUsd: Double

    enum CodingKeys: String, CodingKey {
        case currency
        case dayUsd = "day_usd"
        case weekUsd = "week_usd"
        case monthUsd = "month_usd"
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
