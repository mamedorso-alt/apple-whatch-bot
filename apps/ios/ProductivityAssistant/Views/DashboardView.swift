import SwiftUI

struct DashboardView: View {
    @ObservedObject var viewModel: AppViewModel

    var body: some View {
        ScrollView {
            VStack(spacing: 12) {
                DashboardCard(title: String(localized: "dashboard.card.today")) {
                    Text(statusTitle)
                        .font(.title3.weight(.semibold))
                        .foregroundStyle(.white)
                    Text(statusSubtitle)
                        .font(.footnote)
                        .foregroundStyle(.white.opacity(0.7))
                }

                DashboardCard(title: String(localized: "dashboard.card.insight_preview")) {
                    VStack(alignment: .leading, spacing: 10) {
                        Text(insightPreviewBody)
                            .font(.footnote)
                            .foregroundStyle(.white.opacity(0.88))
                            .lineLimit(6)
                            .frame(maxWidth: .infinity, alignment: .leading)
                        NavigationLink {
                            InsightsView(viewModel: viewModel)
                        } label: {
                            HStack {
                                Text(String(localized: "dashboard.insight.open_full"))
                                    .font(.subheadline.weight(.medium))
                                Spacer()
                                Image(systemName: "chevron.right")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white.opacity(0.45))
                            }
                            .foregroundStyle(AppTheme.accent)
                        }
                    }
                }

                DashboardCard(title: String(localized: "dashboard.card.recovery")) {
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
                    .frame(maxWidth: .infinity)
                }

                DashboardCard(title: String(localized: "dashboard.card.weekly_preview")) {
                    if viewModel.weeklyActivity.isEmpty {
                        Text(String(localized: "weekly_charts.empty"))
                            .font(.footnote)
                            .foregroundStyle(.white.opacity(0.7))
                    } else {
                        let stats = weeklyStats()
                        HStack(spacing: 10) {
                            KPIView(
                                title: String(localized: "dashboard.kpi.avg_steps"),
                                value: Int(stats.avgSteps).formatted(),
                                tint: AppTheme.accent
                            )
                            KPIView(
                                title: String(localized: "dashboard.kpi.avg_kcal"),
                                value: Int(stats.avgKcal).formatted(),
                                tint: AppTheme.warning
                            )
                        }
                    }
                }

                HStack(spacing: 10) {
                    Button(String(localized: "sync.button.sync_now")) {
                        Task { await viewModel.syncNow() }
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(AppTheme.accent)
                    .disabled(viewModel.isLoading)

                    Button(String(localized: "sync.button.refresh_status")) {
                        Task { await viewModel.refreshReportStatus() }
                    }
                    .buttonStyle(.bordered)
                    .disabled(viewModel.isLoading)
                }
                .frame(maxWidth: .infinity, alignment: .leading)

                if let error = viewModel.errorMessage {
                    Text(error)
                        .foregroundStyle(.red)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
            .padding()
        }
        .background(AppTheme.background.ignoresSafeArea())
        .navigationTitle(String(localized: "tab.dashboard"))
        .task {
            await viewModel.refreshReportStatus()
            if viewModel.weeklyActivity.isEmpty {
                await viewModel.fetchWeeklyActivity()
            }
        }
    }

    private var statusTitle: String {
        if viewModel.hasTodayScore {
            return String(localized: "dashboard.status.ready")
        }
        return String(localized: "dashboard.status.waiting")
    }

    private var statusSubtitle: String {
        if let date = viewModel.lastSyncAt {
            return String(format: String(localized: "sync.last_sync"), date.formatted(date: .abbreviated, time: .shortened))
        }
        return String(localized: "sync.last_sync_never")
    }

    private var insightPreviewBody: String {
        let t = viewModel.dailyInsightText.trimmingCharacters(in: .whitespacesAndNewlines)
        if t.isEmpty {
            return String(localized: "dashboard.insight.placeholder")
        }
        return t
    }

    private func weeklyStats() -> (avgSteps: Double, avgKcal: Double) {
        guard viewModel.weeklyActivity.isEmpty == false else {
            return (0, 0)
        }
        let totalSteps = viewModel.weeklyActivity.reduce(0.0) { $0 + $1.steps }
        let totalKcal = viewModel.weeklyActivity.reduce(0.0) { $0 + $1.activeKcal }
        let days = Double(viewModel.weeklyActivity.count)
        return (totalSteps / days, totalKcal / days)
    }
}
