import SwiftUI

struct SyncStatusView: View {
    @ObservedObject var viewModel: AppViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                DashboardCard(title: String(localized: "sync.title")) {
                    if let lastSyncAt = viewModel.lastSyncAt {
                        Text(String(format: String(localized: "sync.last_sync"), lastSyncAt.formatted(date: .abbreviated, time: .shortened)))
                            .foregroundStyle(.white.opacity(0.85))
                    } else {
                        Text(String(localized: "sync.last_sync_never"))
                            .foregroundStyle(.white.opacity(0.85))
                    }

                    Group {
                        Text(String(format: String(localized: "sync.linked"), viewModel.isLinked ? String(localized: "common.yes") : String(localized: "common.no")))
                        Text(String(format: String(localized: "sync.language"), viewModel.profileLanguage))
                        Text(String(format: String(localized: "sync.timezone"), viewModel.profileTimezone))
                        Text(String(format: String(localized: "sync.server_last_sync_date"), viewModel.lastSyncDateFromServer ?? String(localized: "common.na")))
                        Text(String(format: String(localized: "sync.today_score_ready"), viewModel.hasTodayScore ? String(localized: "common.yes") : String(localized: "common.no")))
                    }
                    .font(.footnote)
                    .foregroundStyle(.white.opacity(0.65))
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

                if let error = viewModel.errorMessage {
                    Text(error).foregroundStyle(.red)
                }
            }
            .padding()
        }
        .background(AppTheme.background.ignoresSafeArea())
        .navigationTitle(String(localized: "sync.title"))
        .task {
            if viewModel.apiToken.isEmpty == false && viewModel.lastSyncAt == nil {
                await viewModel.syncNow()
            }
            await viewModel.refreshReportStatus()
        }
    }
}
