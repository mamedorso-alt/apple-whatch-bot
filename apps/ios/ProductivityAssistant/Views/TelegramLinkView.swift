import SwiftUI

struct TelegramLinkView: View {
    @ObservedObject var viewModel: AppViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                DashboardCard(title: String(localized: "telegram_link.title")) {
                    Text(String(localized: "telegram_link.step1"))
                        .foregroundStyle(.white.opacity(0.9))
                    Text(String(localized: "telegram_link.step2"))
                        .foregroundStyle(.white.opacity(0.85))
                    Text(String(localized: "telegram_link.step3"))
                        .foregroundStyle(.white.opacity(0.65))

                    if viewModel.linkCode.isEmpty == false {
                        Text(String(format: String(localized: "telegram_link.code"), viewModel.linkCode))
                            .font(.title3.weight(.bold))
                            .foregroundStyle(AppTheme.accent)
                    }
                }

                Button(String(localized: "telegram_link.button.get_code")) {
                    Task { await viewModel.fetchLinkCode() }
                }
                .buttonStyle(.borderedProminent)
                .tint(AppTheme.accent)
                .disabled(viewModel.isLoading)

                if let error = viewModel.errorMessage {
                    Text(error).foregroundStyle(.red)
                }
            }
            .padding()
        }
        .background(AppTheme.background.ignoresSafeArea())
        .navigationTitle(String(localized: "telegram_link.title"))
    }
}
