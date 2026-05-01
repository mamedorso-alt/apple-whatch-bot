import Foundation

enum AppVersion {
    /// Marketing version + build, e.g. `1.0.1 (2)`.
    static var fullLabel: String {
        let info = Bundle.main.infoDictionary
        let v = info?["CFBundleShortVersionString"] as? String ?? "?"
        let b = info?["CFBundleVersion"] as? String ?? "?"
        return "\(v) (\(b))"
    }
}
