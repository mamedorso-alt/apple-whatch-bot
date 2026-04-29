import SwiftUI

struct RootContentView: View {
    @ObservedObject var viewModel: AppViewModel

    var body: some View {
        NavigationStack {
            List {
                NavigationLink(LocalizedStringKey("nav.onboarding")) {
                    OnboardingView()
                }
                NavigationLink(LocalizedStringKey("nav.health_access")) {
                    HealthAccessView(viewModel: viewModel)
                }
                NavigationLink(LocalizedStringKey("nav.telegram_link")) {
                    TelegramLinkView(viewModel: viewModel)
                }
                NavigationLink(LocalizedStringKey("nav.sync_status")) {
                    SyncStatusView(viewModel: viewModel)
                }
                NavigationLink(LocalizedStringKey("nav.reports")) {
                    ReportsView(viewModel: viewModel)
                }
            }
            .navigationTitle(LocalizedStringKey("nav.productivity_mvp"))
        }
    }
}
