import BackgroundTasks
import Foundation

final class BackgroundSyncManager {
    static let shared = BackgroundSyncManager()
    static let taskIdentifier = "com.productivity.assistant.sync"

    private static var didRegister = false
    private static let registerLock = NSLock()

    private init() {}

    func register() {
        Self.registerLock.lock()
        defer { Self.registerLock.unlock() }
        guard !Self.didRegister else { return }
        Self.didRegister = true
        BGTaskScheduler.shared.register(forTaskWithIdentifier: Self.taskIdentifier, using: nil) { task in
            guard let refreshTask = task as? BGAppRefreshTask else {
                task.setTaskCompleted(success: false)
                return
            }
            self.handle(refreshTask: refreshTask)
        }
    }

    func scheduleAppRefresh() {
        let request = BGAppRefreshTaskRequest(identifier: Self.taskIdentifier)
        request.earliestBeginDate = Date(timeIntervalSinceNow: 15 * 60)
        do {
            try BGTaskScheduler.shared.submit(request)
        } catch {
            // Ignore scheduling errors silently; app can still sync in foreground.
        }
    }

    private func handle(refreshTask: BGAppRefreshTask) {
        scheduleAppRefresh()
        let worker = Task { @MainActor in
            let viewModel = AppViewModel()
            await viewModel.performBackgroundSync()
            refreshTask.setTaskCompleted(success: true)
        }
        refreshTask.expirationHandler = {
            worker.cancel()
            refreshTask.setTaskCompleted(success: false)
        }
    }
}
