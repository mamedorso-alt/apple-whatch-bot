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

    private func validate(response: URLResponse, data: Data) throws {
        guard let http = response as? HTTPURLResponse else { return }
        guard (200 ... 299).contains(http.statusCode) else {
            let text = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw NSError(domain: "ApiClient", code: http.statusCode, userInfo: [NSLocalizedDescriptionKey: text])
        }
    }
}
