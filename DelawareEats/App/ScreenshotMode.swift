import Foundation
import CoreLocation
import UIKit

/// `-screenshot <name>` opens one screen with fixed state for App Store screenshots (scripts/capture-screenshots.sh).
/// Names: home, scrapple, crab, brewpub, italian, creamery, detail, map, honors, saved, about.
enum ScreenshotMode {
    /// Debug builds only: an App Store build ignores the launch argument, so no one can reach seeded screens or fake locations.
    static var name: String? {
        #if DEBUG
        let args = ProcessInfo.processInfo.arguments
        guard let i = args.firstIndex(of: "-screenshot"), i + 1 < args.count else { return nil }
        return args[i + 1]
        #else
        return nil
        #endif
    }
    static var isActive: Bool { name != nil }

    @MainActor
    static func apply(to model: AppModel) {
        guard let name, model.isLoaded else { return }
        model.filters = Filters()
        // Rodney Square, Wilmington, so "nearest" lists have distances without a permission prompt
        model.screenshotLocation = CLLocation(latitude: 39.7462, longitude: -75.5478)
        // by name and town, ignoring case, so a rebuild with a slightly different casing still finds the place; the hand-checked one first.
        // App Store rule: no screenshot shows a negative board (a unit test checks the picks have no follow-up or complaint visit
        // after their latest routine inspection)
        let pick = { (n: String, town: String?) -> Place? in
            let hits = model.places.filter { $0.name.caseInsensitiveCompare(n) == .orderedSame && (town == nil || $0.city == town) }
            return hits.first(where: \.handChecked) ?? hits.first
        }
        for p in Self.savedPicks.compactMap({ pick($0.0, $0.1) }) where !model.isSaved(p) {
            model.toggleSaved(p)
        }
        let open = { (g: Guide) in model.tab = .guides; model.selectedGuide = g; model.guidesPath = [.guide(g)] }
        switch name {
        case "home":
            // the iPad's place column shows Dogfish Head next to Home: measured from Rehoboth Avenue, not 75 miles away in Wilmington
            model.screenshotLocation = CLLocation(latitude: 38.7166, longitude: -75.0786)
            model.tab = .guides; model.selectedGuide = nil
        case "brewpub":
            // from the Rehoboth Avenue bandstand, so the beach brewpubs come first
            model.screenshotLocation = CLLocation(latitude: 38.7166, longitude: -75.0786)
            open(.brewpub)
        case "creamery": open(.creamery)
        case "crab":
            // from Lewes's Second Street, between the bay and the Inland Bays
            model.screenshotLocation = CLLocation(latitude: 38.7746, longitude: -75.1393)
            open(.crab)
        case "scrapple":
            // from Middletown's Main Street: the hand-checked scrapple places run from Smyrna to Wilmington
            model.screenshotLocation = CLLocation(latitude: 39.4496, longitude: -75.7163)
            open(.scrapple)
        case "italian": open(.italian)
        case "honors": open(.honors)
        case "oldest": open(.oldest)
        case "detail":
            open(.scrapple)
            if let p = pick(Self.detailPick.0, Self.detailPick.1) ?? model.places.first { model.selectedPlace = p; model.guidesPath.append(.place(p)) }
        case "map":
            // Rehoboth Beach, zoomed in so individual pins show
            model.screenshotLocation = CLLocation(latitude: 38.7190, longitude: -75.0830)
            model.tab = .map
        case "saved": model.tab = .saved
        case "about": model.tab = .about
        default: model.tab = .guides; model.selectedGuide = nil
        }
        // iPad shows the place column next to every list, so give each shot a place instead of "Pick a place": a hand-checked or
        // honored place from that list. That column shows the whole visit history, so each pick's latest visit is a routine one
        // (a unit test checks).
        guard UIDevice.current.userInterfaceIdiom == .pad, model.selectedPlace == nil else { return }
        let place: Place? = switch name {
        case "home", "brewpub", "map": pick(Self.padPick.0, Self.padPick.1)
        case "crab": pick(Self.crabPick.0, Self.crabPick.1)
        case "scrapple", "italian": pick(Self.scrapplePick.0, Self.scrapplePick.1)
        case "creamery": pick(Self.creameryPick.0, Self.creameryPick.1)
        case "saved", "oldest", "honors": pick(Self.honorPick.0, Self.honorPick.1)
        case "about": nil
        default: pick(Self.detailPick.0, Self.detailPick.1)
        }
        model.selectedPlace = place
    }

    /// the places the screenshots open and save (name, town): hand-checked or honored places with no follow-up or complaint visit
    /// after their latest routine inspection (a unit test checks)
    static let detailPick = ("Helen's Sausage House", "Smyrna")
    static let padPick = ("Dogfish Head", "Rehoboth Beach")
    static let crabPick = ("The Surfing Crab Restaurant and Bar", "Lewes")
    static let scrapplePick = ("Helen's Sausage House", "Smyrna")
    static let creameryPick = ("Woodside Farm Creamery", "Hockessin")
    static let honorPick = ("Bardea Food & Drink", "Wilmington")
    static let savedPicks: [(String, String)] = [("Bardea Food & Drink", "Wilmington"), ("Helen's Sausage House", "Smyrna"), ("Dogfish Head", "Rehoboth Beach")]
}
