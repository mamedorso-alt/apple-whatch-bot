import SwiftUI

struct TelegramLinkView: View {
    @ObservedObject var viewModel: AppViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("1) Нажмите кнопку для получения кода")
            Text("2) Отправьте в Telegram команду: /link CODE")
            Text("3) После привязки используйте /today и /week")
                .foregroundStyle(.secondary)

            Button("Получить код привязки") {
                Task { await viewModel.fetchLinkCode() }
            }
            .buttonStyle(.borderedProminent)
            .disabled(viewModel.isLoading)

            if viewModel.linkCode.isEmpty == false {
                Text("Ваш код: \(viewModel.linkCode)")
                    .font(.title3)
                    .bold()
            }

            if let error = viewModel.errorMessage {
                Text(error).foregroundStyle(.red)
            }
            Spacer()
        }
        .padding()
        .navigationTitle("Telegram Link")
    }
}
