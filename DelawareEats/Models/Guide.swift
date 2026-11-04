import Foundation
import CoreLocation

/// The lists the app is built around. Each is a filter plus an order; none uses ratings (the app only publishes data it may).
enum Guide: String, CaseIterable, Identifiable, Hashable {
    case scrapple, boardwalk, crab, dumplings, italian, creamery, brewpub, honors, oldest, inspections, nearMe, all

    var id: String { rawValue }

    var title: String {
        switch self {
        case .scrapple: "Scrapple Breakfasts"
        case .boardwalk: "Boardwalk Classics"
        case .crab: "Crab Houses & Seafood"
        case .dumplings: "Slippery Dumplings"
        case .italian: "Wilmington Italian"
        case .creamery: "Farm Creameries"
        case .brewpub: "Brewpubs"
        case .honors: "James Beard Honors"
        case .oldest: "Oldest Places"
        case .inspections: "Health Inspections"
        case .nearMe: "Near Me"
        case .all: "All Restaurants"
        }
    }

    var subtitle: String {
        switch self {
        case .scrapple: "Hand-checked places serving scrapple, Delaware's breakfast meat"
        case .boardwalk: "Hand-checked boardwalk standbys at the beach"
        case .crab: "Hand-checked steamed crabs, crab cakes and seafood shacks"
        case .dumplings: "Hand-checked chicken and slippery dumplings"
        case .italian: "Hand-checked family Italian kitchens in and around Wilmington"
        case .creamery: "Hand-checked creameries scooping ice cream made from their own farms' milk"
        case .brewpub: "Hand-checked brewpubs pouring their own beer"
        case .honors: "James Beard finalists and semifinalists"
        case .oldest: "Founding years checked at the same address, oldest first"
        case .inspections: "The Division of Public Health's own inspection records"
        case .nearMe: "Everything around you, closest first"
        case .all: "Restaurants, cafés, bars and bakeries statewide"
        }
    }

    var systemImage: String {
        switch self {
        case .scrapple: "frying.pan"
        case .boardwalk: "sun.max"
        case .crab: "fish"
        case .dumplings: "fork.knife.circle"
        case .italian: "takeoutbag.and.cup.and.straw"
        case .creamery: "snowflake"
        case .brewpub: "mug"
        case .honors: "star.circle"
        case .oldest: "clock.arrow.circlepath"
        case .inspections: "checkmark.seal"
        case .nearMe: "location"
        case .all: "fork.knife"
        }
    }

    /// The hand-checked Delaware guides get the accent card on Home.
    var isDelaware: Bool { tag != nil }

    /// Guides whose order is a ranking worth numbering.
    var isRanked: Bool { [.oldest].contains(self) }

    var sortOptions: [SortOrder] {
        switch self {
        case .scrapple, .boardwalk, .crab, .dumplings, .italian, .creamery, .brewpub: [.featured, .nearest, .name]
        case .honors: [.iconic, .nearest]
        case .oldest: [.oldest]
        case .inspections: [.recent, .fewestCited, .mostCited, .nearest]
        case .nearMe: [.nearest]
        case .all: [.name, .nearest]
        }
    }

    var defaultSort: SortOrder { sortOptions[0] }

    /// The tag behind a hand-checked guide.
    var tag: PlaceTags? {
        switch self {
        case .scrapple: .scrapple
        case .boardwalk: .boardwalk
        case .crab: .crab
        case .dumplings: .dumplings
        case .italian: .italian
        case .creamery: .creamery
        case .brewpub: .brewpub
        default: nil
        }
    }

    func includes(_ p: Place) -> Bool {
        if let tag {   // the guides that promise "hand-checked" list only places checked open with a 2025–26 source
            return p.handChecked && p.tags.contains(tag)
        }
        switch self {
        case .honors: return p.jamesBeard != nil
        case .oldest: return p.founded != nil && p.tags.contains(.oldest)
        // places with a routine DPH inspection in the window: the comparable visit the list sorts by
        case .inspections: return p.inspection?.routineCount != nil
        default: return true
        }
    }
}

enum SortOrder: String, CaseIterable, Identifiable {
    case featured, nearest, oldest, name, iconic, recent, fewestCited, mostCited
    var id: String { rawValue }
    var label: String {
        switch self {
        case .featured: "Featured first"
        case .nearest: "Nearest"
        case .oldest: "Oldest first"
        case .name: "A to Z"
        case .iconic: "Finalists, then semifinalists"
        case .recent: "Latest inspection first"
        case .fewestCited: "Fewest sections cited"
        case .mostCited: "Most sections cited"
        }
    }
}

/// Filters shared by every list. Search text lives with each list.
struct Filters: Equatable, Codable {
    var town: String?
    var cuisine: String?
    var hideChains = false
    var confirmedOnly = false
    var includeNonRestaurants = false
    // no MICHELIN filter: Delaware has no MICHELIN Guide (BIB-GOURMAND-FILTER.md applies only where there's MICHELIN data)

    var activeCount: Int {
        [town != nil, cuisine != nil, hideChains, confirmedOnly, includeNonRestaurants].filter { $0 }.count
    }

    func allows(_ p: Place) -> Bool {
        if !includeNonRestaurants && p.isVenue { return false }
        if let town, p.city != town { return false }
        if let cuisine, p.cuisine != cuisine { return false }
        if hideChains && p.isChain { return false }
        if confirmedOnly && p.tier == .listing { return false }
        return true
    }
}

extension Filters {
    /// Filters saved by an older build may lack a key: read what's there instead of dropping them all.
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        self.init(town: try c.decodeIfPresent(String.self, forKey: .town),
                  cuisine: try c.decodeIfPresent(String.self, forKey: .cuisine),
                  hideChains: try c.decodeIfPresent(Bool.self, forKey: .hideChains) ?? false,
                  confirmedOnly: try c.decodeIfPresent(Bool.self, forKey: .confirmedOnly) ?? false,
                  includeNonRestaurants: try c.decodeIfPresent(Bool.self, forKey: .includeNonRestaurants) ?? false)
    }
}

enum Ranking {
    static func sort(_ places: [Place], by order: SortOrder, from here: CLLocation?) -> [Place] {
        // Keys come from fields made once at load: a localized compare, or a new CLLocation per comparison, made a 16,000-place
        // sort take most of a second (AR-13). sortKey is the normalized name, so case, accents and punctuation don't change the order.
        func name(_ a: Place, _ b: Place) -> Bool { a.sortKey != b.sortKey ? a.sortKey < b.sortKey : a.id < b.id }
        switch order {
        case .nearest where here != nil:
            // each distance once, not four times per comparison
            let from = here!
            return places.map { p in (p, p.location.map { $0.distance(from: from) } ?? .greatestFiniteMagnitude) }
                .sorted { $0.1 != $1.1 ? $0.1 < $1.1 : name($0.0, $1.0) }
                .map(\.0)
        case .featured, .nearest:
            // honored places first, then verified founding year, then name
            return places.sorted {
                let a = $0.iconicPoints ?? -1, b = $1.iconicPoints ?? -1
                if a != b { return a > b }
                let fa = $0.founded ?? 9999, fb = $1.founded ?? 9999
                return fa != fb ? fa < fb : name($0, $1)
            }
        case .oldest:
            return places.sorted { ($0.founded ?? 9999) != ($1.founded ?? 9999) ? ($0.founded ?? 9999) < ($1.founded ?? 9999) : name($0, $1) }
        case .name:
            return places.sorted(by: name)
        case .iconic:
            // an order anyone can check: the James Beard honor (America's Classic, winner, finalist, semifinalist), then name
            func jb(_ p: Place) -> Int { p.honorFlags & 1 != 0 ? 4 : p.honorFlags & 2 != 0 ? 3 : p.honorFlags & 4 != 0 ? 2 : p.honorFlags & 8 != 0 ? 1 : 0 }
            return places.sorted {
                if jb($0) != jb($1) { return jb($0) > jb($1) }
                return name($0, $1)
            }
        case .recent:
            return places.sorted {
                let a = $0.inspection?.lastDate ?? "", b = $1.inspection?.lastDate ?? ""
                return a != b ? a > b : name($0, $1)
            }
        case .fewestCited, .mostCited:
            // the Food Code sections DPH cited at the latest routine inspection (DPH publishes no grade, and this app computes none);
            // places without a routine inspection go last either way, then the newer inspection first
            let fewest = order == .fewestCited
            return places.sorted {
                let a = $0.inspection?.routineCount, b = $1.inspection?.routineCount
                if (a == nil) != (b == nil) { return a != nil }
                let x = a ?? 0, y = b ?? 0
                if x != y { return fewest ? x < y : x > y }
                let da = $0.inspection?.routineDate ?? "", db = $1.inspection?.routineDate ?? ""
                return da != db ? da > db : name($0, $1)
            }
        }
    }
}
