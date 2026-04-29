import SwiftUI

struct SyncStatusView: View {
    @ObservedObject var viewModel: AppViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Button(String(localized: "sync.button.sync_now")) {
                Task { await viewModel.syncNow() }
            }
            .buttonStyle(.borderedProminent)
            .disabled(viewModel.isLoading)

            Button(String(localized: "sync.button.refresh_status")) {
                Task { await viewModel.refreshReportStatus() }
            }
            .buttonStyle(.bordered)
            .disabled(viewModel.isLoading)

            if let lastSyncAt = viewModel.lastSyncAt {
                Text(String(format: String(localized: "sync.last_sync"), lastSyncAt.formatted(date: .abbreviated, time: .shortened)))
            } else {
                Text(String(localized: "sync.last_sync_never"))
            }

            Group {
                Text(String(format: String(localized: "sync.linked"), viewModel.isLinked ? String(localized: "common.yes") : String(localized: "common.no")))
                Text(String(format: String(localized: "sync.language"), viewModel.profileLanguage))
                Text(String(format: String(localized: "sync.timezone"), viewModel.profileTimezone))
                Text(String(format: String(localized: "sync.server_last_sync_date"), viewModel.lastSyncDateFromServer ?? String(localized: "common.na")))
                Text(String(format: String(localized: "sync.today_score_ready"), viewModel.hasTodayScore ? String(localized: "common.yes") : String(localized: "common.no")))
            }
            .font(.footnote)
            .foregroundStyle(.secondary)

            if let error = viewModel.errorMessage {
                Text(error).foregroundStyle(.red)
            }
            Spacer()
        }
        .padding()
        .navigationTitle(String(localized: "sync.title"))
        .task {
            if viewModel.apiToken.isEmpty == false && viewModel.lastSyncAt == nil {
                await viewModel.syncNow()
            }
            await viewModel.refreshReportStatus()
        }
    }
}
