import SwiftUI

enum AppTheme {
    static let background = Color(red: 10 / 255, green: 14 / 255, blue: 23 / 255)
    static let cardBackground = Color(red: 20 / 255, green: 25 / 255, blue: 36 / 255)
    static let accent = Color(red: 72 / 255, green: 170 / 255, blue: 255 / 255)
    static let success = Color(red: 72 / 255, green: 201 / 255, blue: 176 / 255)
    static let warning = Color(red: 255 / 255, green: 179 / 255, blue: 71 / 255)
    static let danger = Color(red: 255 / 255, green: 107 / 255, blue: 107 / 255)
}

struct DashboardCard<Content: View>: View {
    let title: String
    @ViewBuilder var content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title)
                .font(.headline)
                .foregroundStyle(.white.opacity(0.95))
            content
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(AppTheme.cardBackground)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }
}

struct KPIView: View {
    let title: String
    let value: String
    let tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.white.opacity(0.65))
            Text(value)
                .font(.title3.weight(.semibold))
                .foregroundStyle(.white)
            RoundedRectangle(cornerRadius: 2)
                .fill(tint)
                .frame(height: 4)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white.opacity(0.04))
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}
