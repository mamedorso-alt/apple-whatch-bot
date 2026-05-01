import Foundation

final class ApiClient {
    static let shared = ApiClient()

    private init() {}

    private let baseURL: URL = {
        let raw = Bundle.main.object(forInfoDictionaryKey: "API_BASE_URL") as? String
        let fallback = "http://localhost:8000"
        return URL(string: raw ?? fallback) ?? URL(string: fallback)!
    }()
    private let encoder: JSONEncoder = {
        let value = JSONEncoder()
        value.keyEncodingStrategy = .convertToSnakeCase
        return value
    }()
    private let apiDecoder: JSONDecoder = {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        return d
    }()

    func authenticateDevice() async throws -> DeviceAuthResponse {
        let url = baseURL.appending(path: "/v1/auth/device")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: data)
        return try JSONDecoder().decode(DeviceAuthResponse.self, from: data)
    }

    func createLinkCode(apiToken: String) async throws -> LinkCodeResponse {
        let url = baseURL.appending(path: "/v1/telegram/link-code")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(apiToken)", forHTTPHeaderField: "Authorization")
        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: data)
        return try JSONDecoder().decode(LinkCodeResponse.self, from: data)
    }

    func sendDailyMetrics(payload: DailyPayload, apiToken: String) async throws {
        let url = baseURL.appending(path: "/v1/health/daily")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(apiToken)", forHTTPHeaderField: "Authorization")
        request.httpBody = try encoder.encode(payload)
        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: data)
    }

    func getTodayReport(apiToken: String) async throws -> TextReportResponse {
        let url = baseURL.appending(path: "/v1/reports/today")
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("Bearer \(apiToken)", forHTTPHeaderField: "Authorization")
        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: data)
        return try JSONDecoder().decode(TextReportResponse.self, from: data)
    }

    func getWeekReport(apiToken: String) async throws -> TextReportResponse {
        let url = baseURL.appending(path: "/v1/reports/week")
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("Bearer \(apiToken)", forHTTPHeaderField: "Authorization")
        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: data)
        return try JSONDecoder().decode(TextReportResponse.self, from: data)
    }

    func getReportStatus(apiToken: String) async throws -> ReportStatusResponse {
        let url = baseURL.appending(path: "/v1/reports/status")
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("Bearer \(apiToken)", forHTTPHeaderField: "Authorization")
        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: data)
        return try JSONDecoder().decode(ReportStatusResponse.self, from: data)
    }

    func getUserProfile(apiToken: String) async throws -> UserProfileDTO {
        let url = baseURL.appending(path: "/v1/profile")
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("Bearer \(apiToken)", forHTTPHeaderField: "Authorization")
        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: data)
        return try apiDecoder.decode(UserProfileDTO.self, from: data)
    }

    func patchUserProfile(apiToken: String, patch: UserProfilePatch) async throws -> UserProfileDTO {
        let url = baseURL.appending(path: "/v1/profile")
        var request = URLRequest(url: url)
        request.httpMethod = "PATCH"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(apiToken)", forHTTPHeaderField: "Authorization")
        request.httpBody = try encoder.encode(patch)
        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: data)
        return try apiDecoder.decode(UserProfileDTO.self, from: data)
    }

    func postProfileWeight(apiToken: String, weightKg: Double) async throws -> UserProfileDTO {
        let url = baseURL.appending(path: "/v1/profile/weight")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(apiToken)", forHTTPHeaderField: "Authorization")
        request.httpBody = try encoder.encode(WeightIngestPayload(weightKg: weightKg))
        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: data)
        return try apiDecoder.decode(UserProfileDTO.self, from: data)
    }

    func postProfileSubjective(apiToken: String, payload: SubjectiveDailyPayload) async throws -> SubjectiveSaveResponse {
        let url = baseURL.appending(path: "/v1/profile/subjective")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(apiToken)", forHTTPHeaderField: "Authorization")
        let plainEncoder = JSONEncoder()
        request.httpBody = try plainEncoder.encode(payload)
        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: data)
        return try apiDecoder.decode(SubjectiveSaveResponse.self, from: data)
    }

    func getDailyInsights(apiToken: String) async throws -> InsightTextResponse {
        let url = baseURL.appending(path: "/v1/insights/daily")
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("Bearer \(apiToken)", forHTTPHeaderField: "Authorization")
        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: data)
        return try apiDecoder.decode(InsightTextResponse.self, from: data)
    }

    func getWeeklyInsights(apiToken: String) async throws -> InsightTextResponse {
        let url = baseURL.appending(path: "/v1/insights/weekly")
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("Bearer \(apiToken)", forHTTPHeaderField: "Authorization")
        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: data)
        return try apiDecoder.decode(InsightTextResponse.self, from: data)
    }

    func getAgentSpend(apiToken: String) async throws -> AgentSpendResponse {
        let url = baseURL.appending(path: "/v1/usage/spend")
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("Bearer \(apiToken)", forHTTPHeaderField: "Authorization")
        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: data)
        return try apiDecoder.decode(AgentSpendResponse.self, from: data)
    }

    private func validate(response: URLResponse, data: Data) throws {
        guard let http = response as? HTTPURLResponse else { return }
        guard (200 ... 299).contains(http.statusCode) else {
            let text = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw NSError(domain: "ApiClient", code: http.statusCode, userInfo: [NSLocalizedDescriptionKey: text])
        }
    }
}
