import SwiftUI

struct HealthAccessView: View {
    @ObservedObject var viewModel: AppViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                DashboardCard(title: String(localized: "health_access.title")) {
                    Text(String(localized: "health_access.prompt"))
                        .foregroundStyle(.white.opacity(0.9))
                    Text(String(localized: "health_access.list"))
                        .font(.footnote)
                        .foregroundStyle(.white.opacity(0.65))
                }

                Button(viewModel.healthAccessGranted ? String(localized: "health_access.button.granted") : String(localized: "health_access.button.allow")) {
                    Task { await viewModel.requestHealthAccess() }
                }
                .buttonStyle(.borderedProminent)
                .tint(AppTheme.accent)
                .disabled(viewModel.isLoading || viewModel.healthAccessGranted)

                if let error = viewModel.errorMessage {
                    Text(error).foregroundStyle(.red)
                }
            }
            .padding()
        }
        .background(AppTheme.background.ignoresSafeArea())
        .navigationTitle(String(localized: "health_access.title"))
        .onAppear {
            viewModel.clearError()
            Task { await viewModel.refreshHealthAccessState() }
        }
    }
}
