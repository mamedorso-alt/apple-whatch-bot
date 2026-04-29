import SwiftUI

struct TelegramLinkView: View {
    @ObservedObject var viewModel: AppViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(String(localized: "telegram_link.step1"))
            Text(String(localized: "telegram_link.step2"))
            Text(String(localized: "telegram_link.step3"))
                .foregroundStyle(.secondary)

            Button(String(localized: "telegram_link.button.get_code")) {
                Task { await viewModel.fetchLinkCode() }
            }
            .buttonStyle(.borderedProminent)
            .disabled(viewModel.isLoading)

            if viewModel.linkCode.isEmpty == false {
                Text(String(format: String(localized: "telegram_link.code"), viewModel.linkCode))
                    .font(.title3)
                    .bold()
            }

            if let error = viewModel.errorMessage {
                Text(error).foregroundStyle(.red)
            }
            Spacer()
        }
        .padding()
        .navigationTitle(String(localized: "telegram_link.title"))
    }
}
