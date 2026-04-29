import SwiftUI

@main
struct ProductivityAssistantApp: App {
    @StateObject private var viewModel = AppViewModel()

    var body: some Scene {
        WindowGroup {
            RootContentView(viewModel: viewModel)
        }
    }
}
