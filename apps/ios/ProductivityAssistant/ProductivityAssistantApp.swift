import SwiftUI

@main
struct ProductivityAssistantApp: App {
    @StateObject private var viewModel = AppViewModel()
    @Environment(\.scenePhase) private var scenePhase

    init() {
        BackgroundSyncManager.shared.register()
        BackgroundSyncManager.shared.scheduleAppRefresh()
    }

    var body: some Scene {
        WindowGroup {
            RootContentView(viewModel: viewModel)
                .task {
                    await viewModel.autoSyncIfStale(maxAgeMinutes: 20)
                    await viewModel.startAutomaticHealthSync()
                }
                .onChange(of: scenePhase) { _, newPhase in
                    switch newPhase {
                    case .active:
                        Task {
                            await viewModel.autoSyncIfStale(maxAgeMinutes: 20)
                            await viewModel.startAutomaticHealthSync()
                        }
                    case .background:
                        BackgroundSyncManager.shared.scheduleAppRefresh()
                    default:
                        break
                    }
                }
        }
    }
}
