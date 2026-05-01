import SwiftUI

struct ProfileHubView: View {
    @ObservedObject var viewModel: AppViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                DashboardCard(title: String(localized: "profile.card.status")) {
                    HStack(spacing: 10) {
                        KPIView(
                            title: String(localized: "dashboard.kpi.connection"),
                            value: viewModel.isLinked ? String(localized: "dashboard.kpi.value.linked") : String(localized: "dashboard.kpi.value.not_linked"),
                            tint: viewModel.isLinked ? AppTheme.success : AppTheme.warning
                        )
                        KPIView(
                            title: String(localized: "dashboard.kpi.score"),
                            value: viewModel.hasTodayScore ? String(localized: "dashboard.kpi.value.ready") : String(localized: "dashboard.kpi.value.missing"),
                            tint: viewModel.hasTodayScore ? AppTheme.success : AppTheme.danger
                        )
                    }
                    Text(String(format: String(localized: "sync.timezone"), viewModel.profileTimezone))
                        .font(.footnote)
                        .foregroundStyle(.white.opacity(0.65))
                }

                DashboardCard(title: String(localized: "profile.card.quick_actions")) {
                    NavigationLink {
                        SyncStatusView(viewModel: viewModel)
                    } label: {
                        profileActionRow(title: String(localized: "nav.sync_status"), icon: "arrow.trianglehead.2.clockwise")
                    }
                    .buttonStyle(.plain)
                    NavigationLink {
                        TelegramLinkView(viewModel: viewModel)
                    } label: {
                        profileActionRow(title: String(localized: "nav.telegram_link"), icon: "paperplane.fill")
                    }
                    .buttonStyle(.plain)
                    NavigationLink {
                        HealthAccessView(viewModel: viewModel)
                    } label: {
                        profileActionRow(title: String(localized: "nav.health_access"), icon: "heart.text.square.fill")
                    }
                    .buttonStyle(.plain)
                    NavigationLink {
                        HealthProfileView(viewModel: viewModel)
                    } label: {
                        profileActionRow(title: String(localized: "nav.health_profile"), icon: "person.text.rectangle.fill")
                    }
                    .buttonStyle(.plain)
                    NavigationLink {
                        InsightsView(viewModel: viewModel)
                    } label: {
                        profileActionRow(title: String(localized: "nav.insights"), icon: "lightbulb.max.fill")
                    }
                    .buttonStyle(.plain)
                    NavigationLink {
                        AgentSpendView(viewModel: viewModel)
                    } label: {
                        profileActionRow(title: String(localized: "nav.agent_spend"), icon: "dollarsign.circle.fill")
                    }
                    .buttonStyle(.plain)
                    NavigationLink {
                        OnboardingView()
                    } label: {
                        profileActionRow(title: String(localized: "nav.onboarding"), icon: "info.circle.fill")
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding()
        }
        .background(AppTheme.background.ignoresSafeArea())
        .navigationTitle(String(localized: "tab.profile"))
        .task {
            await viewModel.refreshReportStatus()
        }
    }

    private func profileActionRow(title: String, icon: String) -> some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .foregroundStyle(AppTheme.accent)
            Text(title)
                .foregroundStyle(.white.opacity(0.92))
            Spacer()
            Image(systemName: "chevron.right")
                .foregroundStyle(.white.opacity(0.4))
        }
        .padding(.vertical, 4)
    }
}
