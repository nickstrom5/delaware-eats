import Foundation
import Observation
import CoreLocation

/// The whole app's state: the bundled places, filters, saved places and what's selected.
@MainActor
@Observable
final class AppModel {
    private(set) var places: [Place] = []
    private(set) var isLoaded = false
    private(set) var loadError: String?
    private(set) var generated = ""
    private(set) var restaurantCount = 0
    /// restaurants with a routine DPH inspection in the feed's two years
    var inspectedCount: Int { places.filter { !$0.isVenue && $0.inspection?.routineCount != nil }.count }
    /// restaurants matched to a live DPH establishment or a current Revenue restaurant license
    var licensedCount: Int { places.filter { !$0.isVenue && $0.tier == .licensed }.count }
    private(set) var calibration = Calibration(areas: [:])
    /// the last day of DPH inspections shown ("dph")
    private(set) var inspectionsThrough: [String: String] = [:]
    var dphThrough: String? { inspectionsThrough["dph"] }
    /// DPH establishments it doesn't mark closed, and current Revenue restaurant licenses
    private(set) var dphLive: Int?
    private(set) var revenueLicenses: Int?
    /// DPH's inspection types ("Routine", "Follow-up", "Complaint") and the Food Code sections' titles, verbatim
    private(set) var visitTypes: [String] = []
    private(set) var sectionTitles: [String: String] = [:]
    /// the Overture Maps release the listings come from, read from the data file
    private(set) var overtureRelease: String?
    /// towns sorted by how many restaurants they have
    private(set) var towns: [(name: String, count: Int)] = []
    private(set) var cuisines: [(name: String, count: Int)] = []
    /// Bib Gourmand places (non-restaurants left out, like the other counts): the Filters switch shows only when there are some.
    private(set) var bibCount = 0
    /// normalized town name -> display name ("canon city" -> "Cañon City")
    private(set) var townKeys: [String: String] = [:]

    var filters = Filters() { didSet { saveFilters() } }
    private(set) var saved: Set<String> = []

    // navigation (iPad sidebar / iPhone tabs)
    var selectedGuide: Guide?
    var selectedPlace: Place?
    var tab: Tab = .guides
    enum Tab: Hashable { case guides, map, saved, about }
    /// the iPhone guides stack: a guide, then a place
    var guidesPath: [Route] = []
    enum Route: Hashable { case guide(Guide), place(Place) }
    /// bumped by openGuide so the iPad sidebar follows even when the same guide is picked again
    private(set) var guideRequest = 0
    /// iPad to iPhone-size (Split View, Stage Manager): the place that was open next to the Map or Saved list, for that tab's own
    /// stack to show, so a size-class change doesn't lose it
    var handoffPlace: Place?

    /// The iPhone guides stack for what's selected: the open guide, then the open place.
    var compactPath: [Route] {
        (selectedGuide.map { [Route.guide($0)] } ?? []) + (selectedPlace.map { [Route.place($0)] } ?? [])
    }

    /// iPhone: the stack changed (a push, a pop, a swipe back), so the selection follows it; an iPad layout then opens on the same
    /// guide and place.
    func followPath() {
        var guide: Guide?
        for r in guidesPath { if case .guide(let g) = r { guide = g } }
        if selectedGuide != guide { selectedGuide = guide }
        if case .place(let p) = guidesPath.last { if selectedPlace != p { selectedPlace = p } } else if selectedPlace != nil { selectedPlace = nil }
    }

    /// Open a guide from Home: pushes it on iPhone, selects it in the iPad sidebar.
    func openGuide(_ g: Guide) {
        tab = .guides
        selectedGuide = g
        guidesPath = [.guide(g)]
        guideRequest += 1
    }

    /// a fixed "you are here" for screenshots, so lists sort by distance without a permission prompt
    var screenshotLocation: CLLocation?

    private let defaults: UserDefaults

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        saved = Set(defaults.stringArray(forKey: "saved") ?? [])
        if let data = defaults.data(forKey: "filters"), let f = try? JSONDecoder().decode(Filters.self, from: data) { filters = f }
    }

    /// A cold launch from Spotlight asks for the data twice (the app's .task and the search continuation); both wait on one decode.
    private var loading: Task<Void, Never>?
    /// every place's detail record (inspection history, license, phone, website), read with the places from the one data file
    @ObservationIgnored private var details: [String: PlaceDetail] = [:]

    /// The detail record for a place (inspection history, license, phone, website). Nil when the place has none.
    func detail(for p: Place) async -> PlaceDetail? { details[p.id] }

    /// Reads places.json's "detail": here, and in the check a downloaded copy passes (DataLayout.app).
    nonisolated static func readDetail(_ root: [String: Any]) throws -> [String: PlaceDetail] {
        guard let d = root["detail"] else { return [:] }
        return try JSONDecoder().decode([String: PlaceDetail].self, from: JSONSerialization.data(withJSONObject: d))
    }

    func load(from url: URL? = AppData.url("places")) async {
        guard !isLoaded else { return }
        if let loading { await loading.value; return }
        let task = Task { await decode(from: url) }
        loading = task
        await task.value
    }

    private func decode(from url: URL?) async {
        guard let url else { loadError = "The restaurant data is missing from the app."; return }
        do {
            let (file, places, details) = try await Task.detached(priority: .userInitiated) { try AppModel.readAll(url) }.value
            self.details = details
            apply(file: file, places: places)
        } catch {
            // a downloaded copy this build can't read (OTA-DATA.md): back to the data built into the app
            if let bundled = AppData.fallback(from: url) { return await decode(from: bundled) }
            loadError = "The restaurant data couldn't be read (\(error.localizedDescription))."
        }
    }

    /// Reads a places.json: launch, and the check a downloaded copy passes before it's stored (DataLayout.app, OTA-DATA.md).
    nonisolated static func read(_ url: URL) throws -> (DataFile, [Place]) {
        let (file, places, _) = try readAll(url)
        return (file, places)
    }

    /// The places and every place's detail record, from one places.json.
    nonisolated static func readAll(_ url: URL) throws -> (DataFile, [Place], [String: PlaceDetail]) {
        let data = try Data(contentsOf: url)
        guard let root = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw DataFile.Malformed(field: "everything") }
        let file = try DataFile(json: root)
        // kept in A-to-Z order: a filter keeps it, so the A-to-Z sort of any list is a pass over an already sorted array
        let places = Place.build(root["places"] as? [[String: Any]] ?? [], file: file)
            .sorted { $0.sortKey != $1.sortKey ? $0.sortKey < $1.sortKey : $0.id < $1.id }
        let details = try readDetail(root)
        return (file, places, details)
    }

    func apply(file: DataFile, places: [Place]) {
        self.places = places
        generated = file.generated
        restaurantCount = file.count_restaurants
        calibration = file.calibration
        inspectionsThrough = file.inspections_through
        dphLive = file.dph_live
        revenueLicenses = file.rev_licenses
        visitTypes = file.itypes
        sectionTitles = file.sections
        overtureRelease = file.overture_release
        var tc: [String: Int] = [:], cc: [String: Int] = [:]
        for p in places where !p.isVenue {
            if let c = p.city { tc[c, default: 0] += 1 }
            cc[p.cuisine, default: 0] += 1
        }
        towns = tc.map { ($0.key, $0.value) }.sorted { $0.count != $1.count ? $0.count > $1.count : $0.name < $1.name }
        cuisines = cc.map { ($0.key, $0.value) }.sorted { $0.count != $1.count ? $0.count > $1.count : $0.name < $1.name }
        bibCount = places.lazy.filter { !$0.isVenue && $0.michelin == .bib }.count
        var keys: [String: String] = [:]
        for (name, _) in towns {   // biggest town wins a shared spelling
            let k = Search.normalizeAddress(name)
            if keys[k] == nil { keys[k] = name }
        }
        townKeys = keys
        if let t = filters.town, tc[t] == nil { filters.town = nil }
        if let c = filters.cuisine, cc[c] == nil { filters.cuisine = nil }
        isLoaded = true
    }

    func place(id: String) -> Place? { places.first { $0.id == id } }

    /// The last list asked for. A list view's body runs on every change (an iPad row tap re-renders it), so the same guide, sort,
    /// search, filters and (for a distance sort) location to ~100 m reuse the result instead of filtering 17,000 places again.
    private struct ListKey: Equatable {
        let guide: Guide, sort: SortOrder, search: String, filters: Filters, count: Int, lat: Int?, lon: Int?
    }
    @ObservationIgnored private var lastList: (key: ListKey, places: [Place])?

    /// Places in a guide, filtered and searched, in the chosen order.
    func list(_ guide: Guide, sort: SortOrder, search: String, here: CLLocation?) -> [Place] {
        // reading filters and places here keeps SwiftUI observing them even when the cached list is returned
        let usesHere = sort == .nearest || guide == .nearMe
        let key = ListKey(guide: guide, sort: sort, search: search, filters: filters, count: places.count,
                          lat: usesHere ? here.map { Int(($0.coordinate.latitude * 1000).rounded()) } : nil,
                          lon: usesHere ? here.map { Int(($0.coordinate.longitude * 1000).rounded()) } : nil)
        if let lastList, lastList.key == key { return lastList.places }
        let out = makeList(guide, sort: sort, search: search, here: usesHere ? here : nil)
        lastList = (key, out)
        return out
    }

    private func makeList(_ guide: Guide, sort: SortOrder, search: String, here: CLLocation?) -> [Place] {
        let q = Search.parse(search, towns: townKeys)
        // typed something, but nothing searchable ("🍕", "!!!"): show nothing rather than everything
        if q.isEmpty && !search.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { return [] }
        var out = places.filter { guide.includes($0) && filters.allows($0) && (q.isEmpty || Search.matches($0, q)) }
        if guide == .nearMe && here == nil { return [] }
        out = Ranking.sort(out, by: sort, from: here)
        if !q.tokens.isEmpty && !(guide.isRanked) {   // name matches first when searching
            let named = out.filter { Search.nameMatches($0, q) }
            if !named.isEmpty && named.count < out.count {
                let ids = Set(named.map(\.id))
                out = named + out.filter { !ids.contains($0.id) }
            }
        }
        return out
    }

    func count(_ guide: Guide) -> Int { places.lazy.filter { guide.includes($0) && self.filters.allows($0) }.count }

    // MARK: saved places

    func isSaved(_ p: Place) -> Bool { saved.contains(p.id) }

    func toggleSaved(_ p: Place) {
        if saved.contains(p.id) { saved.remove(p.id) } else { saved.insert(p.id) }
        defaults.set(Array(saved).sorted(), forKey: "saved")
    }

    var savedPlaces: [Place] { places.filter { saved.contains($0.id) }.sorted { $0.sortKey != $1.sortKey ? $0.sortKey < $1.sortKey : $0.id < $1.id } }

    /// A random place from a guide ("Surprise me"), never the one just shown.
    func randomPick(from guide: Guide, excluding last: String?) -> Place? {
        let pool = places.filter { guide.includes($0) && filters.allows($0) && $0.id != last }
        return pool.randomElement()
    }

    /// "Surprise me": a random hand-checked Delaware pick (any guide), never the one just shown.
    func randomClassic(excluding last: String?) -> Place? {
        places.filter { $0.isClassic && filters.allows($0) && $0.id != last }.randomElement()
    }

    private func saveFilters() {
        if let data = try? JSONEncoder().encode(filters) { defaults.set(data, forKey: "filters") }
    }

    // MARK: honest labels

    /// "73%": how often a listing of this kind matched an inspected DPH establishment, statewide.
    func matchRate(for p: Place) -> String? {
        guard p.tier != .licensed else { return nil }   // an official record confirms it; no listing rate needed
        let group: String
        switch (p.source, p.tier) {
        case ("meta", .confirmed): group = "meta_high"
        case ("meta", _): group = "meta_mid"
        case ("AllThePlaces", _), ("DAC", _): group = "brand_feed"
        default: return nil
        }
        guard let v = calibration.areas["Delaware"]?.groups[group]?.official else { return nil }
        return "\(Int((v * 100).rounded()))%"
    }

    func visitType(_ i: Int) -> String { i >= 0 && i < visitTypes.count ? visitTypes[i] : "" }
    func sectionTitle(_ code: String) -> String { sectionTitles[code] ?? "" }
}
