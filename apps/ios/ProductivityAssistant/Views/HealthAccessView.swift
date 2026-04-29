import SwiftUI

struct HealthAccessView: View {
    @ObservedObject var viewModel: AppViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(String(localized: "health_access.prompt"))
            Text(String(localized: "health_access.list"))
                .font(.footnote)
                .foregroundStyle(.secondary)

            Button(viewModel.healthAccessGranted ? String(localized: "health_access.button.granted") : String(localized: "health_access.button.allow")) {
                Task { await viewModel.requestHealthAccess() }
            }
            .buttonStyle(.borderedProminent)
            .disabled(viewModel.isLoading || viewModel.healthAccessGranted)

            if let error = viewModel.errorMessage {
                Text(error).foregroundStyle(.red)
            }

            Spacer()
        }
        .padding()
        .navigationTitle(String(localized: "health_access.title"))
    }
}
