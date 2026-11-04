import Foundation
import CoreLocation
import SwiftUI

// MARK: - The bundled data (Resources/places.json), written by pipeline/delaware.py with DE_APP=1
// One file for all of Delaware (about 3,000 places): the list, search and map columns in "places", and each place's detail (DPH
// inspection history, its Revenue business license, phone, website) in "detail", keyed by the place's id.

/// The file's header (everything but the places). Read with JSONSerialization, not Codable: thousands of keyed records through
/// JSONDecoder made launch slow (Florida's lesson).
struct DataFile {
    let generated: String
    /// the Overture Maps release the listings come from ("2026-10-21.0")
    let overture_release: String?
    /// DPH establishments inspected in the feed's two years and not marked closed; current Revenue restaurant licenses
    let dph_live: Int?
    let rev_licenses: Int?
    /// the last day of DPH inspections shown ("dph")
    let inspections_through: [String: String]
    let cities: [String]
    let cuisines: [String]
    let brands: [String]
    let counties: [String]
    let srcs: [String]
    /// DPH's inspection types: "Routine", "Follow-up", "Complaint"
    let itypes: [String]
    /// Food Code section -> its title, as DPH publishes it ("6-501.111" -> "Controlling Pests")
    let sections: [String: String]
    let count_restaurants: Int
    let calibration: Calibration

    struct Malformed: LocalizedError { let field: String; var errorDescription: String? { "the data file is missing \(field)" } }

    init(json r: [String: Any]) throws {
        func str(_ k: String) throws -> String { guard let v = r[k] as? String else { throw Malformed(field: k) }; return v }
        func list(_ k: String) throws -> [String] { guard let v = r[k] as? [String] else { throw Malformed(field: k) }; return v }
        generated = try str("generated")
        overture_release = r["overture_release"] as? String
        dph_live = r["dph_live"] as? Int
        rev_licenses = r["rev_licenses"] as? Int
        inspections_through = (r["inspections_through"] as? [String: String]) ?? [:]
        cities = try list("cities"); cuisines = try list("cuisines"); brands = try list("brands"); counties = try list("counties")
        srcs = try list("srcs"); itypes = (r["itypes"] as? [String]) ?? ["Routine", "Follow-up", "Complaint"]
        sections = (r["sections"] as? [String: String]) ?? [:]
        guard let n = r["count_restaurants"] as? Int else { throw Malformed(field: "count_restaurants") }
        count_restaurants = n
        let cal = (r["calibration"] as? [String: Any]).flatMap { try? JSONSerialization.data(withJSONObject: $0) }
        calibration = cal.flatMap { try? JSONDecoder().decode(Calibration.self, from: $0) } ?? Calibration(areas: [:])
    }
}

/// How often listings of one kind matched DPH's establishments, statewide and per county (pipeline/calibrate.py):
/// {"Delaware": {"groups": {"meta_high": {"n": 1908, "official": 0.733}, ...}}, "New Castle County": {...}, ...}
struct Calibration: Decodable, Hashable {
    let areas: [String: CalibrationScope]

    init(areas: [String: CalibrationScope]) { self.areas = areas }
    init(from decoder: Decoder) throws {
        areas = try decoder.singleValueContainer().decode([String: CalibrationScope].self)
    }
}

struct CalibrationScope: Decodable, Hashable {
    let groups: [String: CalibrationGroup]
}

struct CalibrationGroup: Decodable, Hashable {
    let n: Int
    let official: Double
}

/// DPH's latest inspections of a place (core file): [sections cited at the latest routine inspection (null when DPH made only
/// follow-up or complaint visits in the window), that inspection's date, the latest inspection's date, its sections cited, its type].
/// Delaware has no official grade, score or placard, and this app computes none: the count is the Food Code sections DPH cited.
struct InspectionRecord: Hashable {
    /// Food Code sections cited at the latest routine inspection: what lists sort by (fewer first)
    let routineCount: Int?
    let routineDate: String?
    let lastDate: String
    let lastCount: Int
    /// index into DataFile.itypes: 0 Routine, 1 Follow-up, 2 Complaint
    let lastType: Int

    /// a follow-up or complaint visit came after the latest routine inspection
    var hasLaterVisit: Bool { routineDate.map { lastDate > $0 } ?? true }

    /// From the JSONSerialization array (the launch path); nil when a field is missing.
    init?(array a: [Any]) {
        guard a.count >= 5, let ld = a[2] as? String, let ln = a[3] as? Int, let lt = a[4] as? Int else { return nil }
        routineCount = a[0] as? Int; routineDate = a[1] as? String; lastDate = ld; lastCount = ln; lastType = lt
    }

    init(routineCount: Int?, routineDate: String?, lastDate: String, lastCount: Int, lastType: Int) {
        self.routineCount = routineCount; self.routineDate = routineDate; self.lastDate = lastDate; self.lastCount = lastCount; self.lastType = lastType
    }
}

/// One DPH inspection: [date, type index, Food Code sections cited, [section numbers]].
struct InspectionVisit: Decodable, Hashable {
    let d: String
    let t: Int
    let count: Int
    let codes: [String]

    init(from decoder: Decoder) throws {
        var c = try decoder.unkeyedContainer()
        d = try c.decode(String.self)
        t = try c.decode(Int.self)
        count = try c.decode(Int.self)
        codes = try c.decodeIfPresent([String].self) ?? []
    }
}

/// The place's DPH record (detail): routine inspections in the window and every inspection, latest first.
struct InspectionDetail: Decodable, Hashable {
    let n: Int?
    let h: [InspectionVisit]?

    var visits: [InspectionVisit] { h ?? [] }
}

/// The Revenue business license on the place: [source ("Delaware business license"), license number, activity ("Retailer – Restaurant"),
/// the date it's valid through]. A license runs up to three years, so it confirms a business, not that it's open.
struct License: Decodable, Hashable {
    let source: String
    let id: String?
    let type: String
    let validThrough: String?

    init(from decoder: Decoder) throws {
        var c = try decoder.unkeyedContainer()
        source = try c.decode(String.self)
        id = try c.decodeIfPresent(String.self)
        type = try c.decode(String.self)
        validThrough = c.isAtEnd ? nil : try c.decodeIfPresent(String.self)
    }
}

/// A place's detail record, from places.json's "detail".
struct PlaceDetail: Decodable, Hashable {
    let lic: [License]?
    let ph: String?
    let w: String?
    let inspection: InspectionDetail?

    enum CodingKeys: String, CodingKey {
        case lic, ph, w
        case inspection = "in"
    }

    /// web links only: a bare host gets https://, and any other scheme (javascript:, tel:, a custom app URL) is dropped
    var website: URL? {
        w.flatMap { URL(string: $0.contains("://") ? $0 : "https://" + $0) }
            .flatMap { ["http", "https"].contains($0.scheme?.lowercased() ?? "") && $0.host != nil ? $0 : nil }
    }
    var licenses: [License] { lic ?? [] }
}

struct PlaceRecord {
    // the memberwise initializer is used by init?(_ d:) below
    let id: String
    let n: String
    let c: Int?
    let cu: Int
    let t: Int
    let s: Int
    let co: Int?
    let a: String?
    let z: String?
    let la: Double?
    let lo: Double?
    let b: Int?
    let ch: Int?
    let v: Int?
    let bar: Int?
    let liq: Int?
    let g: Int?
    let hc: Int?
    let h: Int?
    let mi: Int?
    let jbf: String?
    let ip: Double?
    let f: Int?
    let fn: String?
    let note: String?
    let dish: String?
    let seas: String?
    /// the listing's other name when a hand-checked place shows its verified one ("Cafe Versailles Calle 8"): searchable, shown small
    let aka: String?
    let inspection: InspectionRecord?
}

extension PlaceRecord {
    /// From one JSONSerialization dictionary (the fast path); nil when the required fields are missing.
    init?(_ d: [String: Any]) {
        guard let id = d["id"] as? String, let n = d["n"] as? String, let cu = d["cu"] as? Int, let t = d["t"] as? Int, let s = d["s"] as? Int else { return nil }
        func i(_ k: String) -> Int? { d[k] as? Int }
        func str(_ k: String) -> String? { d[k] as? String }
        self.init(id: id, n: n, c: i("c"), cu: cu, t: t, s: s, co: i("co"), a: str("a"), z: str("z"), la: d["la"] as? Double,
                  lo: d["lo"] as? Double, b: i("b"), ch: i("ch"), v: i("v"), bar: i("bar"), liq: i("liq"), g: i("g"), hc: i("hc"), h: i("h"),
                  mi: i("mi"), jbf: str("jbf"), ip: d["ip"] as? Double, f: i("f"), fn: str("fn"), note: str("note"), dish: str("dish"),
                  seas: str("seas"), aka: str("aka"),
                  inspection: (d["in"] as? [Any]).flatMap { InspectionRecord(array: $0) })
    }
}

// MARK: - The model the views use

struct PlaceTags: OptionSet, Hashable {
    let rawValue: Int
    // the bits pipeline/delaware.py writes (TAGS there, in this order)
    static let scrapple = PlaceTags(rawValue: 1)    // hand-checked scrapple breakfasts
    static let boardwalk = PlaceTags(rawValue: 2)   // hand-checked boardwalk classics (Rehoboth, Dewey, Bethany)
    static let crab = PlaceTags(rawValue: 4)        // hand-checked crab houses and seafood shacks
    static let dumplings = PlaceTags(rawValue: 8)   // hand-checked chicken and slippery dumplings
    static let italian = PlaceTags(rawValue: 16)    // hand-checked Wilmington Italian
    static let creamery = PlaceTags(rawValue: 32)   // hand-checked farm creameries
    static let brewpub = PlaceTags(rawValue: 64)    // hand-checked brewpubs
    static let oldest = PlaceTags(rawValue: 128)    // hand-checked, open at this address since 1960 or earlier

    /// the chips and Spotlight words for the hand-checked guides
    static let labels: [(PlaceTags, String)] = [(.scrapple, "Scrapple"), (.boardwalk, "Boardwalk classic"), (.crab, "Crab house & seafood"),
                                                (.dumplings, "Slippery dumplings"), (.italian, "Wilmington Italian"),
                                                (.creamery, "Farm creamery"), (.brewpub, "Brewpub")]
}

/// How a place got on the list. The share that matched a license comes from calibration.
enum Tier: Int, Comparable {
    case listing = 0        // one map listing
    case confirmed = 1      // a high-confidence Meta listing, or a hand-checked place
    case licensed = 2       // a live DPH food establishment or a current Revenue restaurant license

    static func < (a: Tier, b: Tier) -> Bool { a.rawValue < b.rawValue }

    var label: String {
        switch self {
        case .licensed: "On an official list"
        case .confirmed: "High-confidence listing"
        case .listing: "Listing only"
        }
    }
}

enum Michelin: Int {
    case none = 0, recommended = 1, bib = 2, oneStar = 3, twoStars = 4, threeStars = 5
    var label: String? {
        switch self {
        case .none: nil
        case .recommended: "MICHELIN Recommended"
        case .bib: "Bib Gourmand"
        case .oneStar: "1 MICHELIN Star"
        case .twoStars: "2 MICHELIN Stars"
        case .threeStars: "3 MICHELIN Stars"
        }
    }
}

struct Place: Identifiable, Hashable {
    let id: String
    let name: String
    let address: String?
    let city: String?
    let county: String?
    let zip: String?
    let coordinate: CLLocationCoordinate2D?
    let cuisine: String
    let brand: String?
    let chainCount: Int
    let tier: Tier
    let source: String
    let isVenue: Bool
    let isBar: Bool
    let tags: PlaceTags
    /// On our hand-checked list (data/research): confirmed open with a 2025–26 source.
    let handChecked: Bool
    let honorFlags: Int
    let michelin: Michelin
    let iconicPoints: Double?
    let jamesBeard: String?
    let founded: Int?
    let foundedNote: String?
    let note: String?
    let dishes: String?
    let seasonal: String?
    let inspection: InspectionRecord?
    /// normalized text for search: name, town, county, zip, cuisine, brand, dishes, then the address with street words abbreviated
    let searchText: String
    let nameText: String
    /// the A-to-Z key, worked out once at load: the normalized name ("por wine house" for "/pôr/ Wine House"), so case, accents
    /// and leading punctuation don't change the order, and a sort never runs a localized compare per comparison
    let sortKey: String
    /// made once at load: a new CLLocation per comparison made a Nearest sort of 16,000 places take seconds
    let location: CLLocation?

    static func == (a: Place, b: Place) -> Bool { a.id == b.id }
    func hash(into h: inout Hasher) { h.combine(id) }

    /// MICHELIN, James Beard or a verified founding year: what the map and Spotlight put first
    var isHonored: Bool { honorFlags != 0 || michelin != .none }
    /// what the Honors section lists: a MICHELIN distinction or a James Beard honor ("oldest" alone isn't an honor)
    var hasHonors: Bool { michelin != .none || jamesBeard != nil }
    var isChain: Bool { chainCount >= 5 }
    var jamesBeardLabel: String? {
        if honorFlags & 1 != 0 { return "America's Classic" }
        if honorFlags & 2 != 0 { return "James Beard winner" }
        if honorFlags & 4 != 0 { return "James Beard finalist" }
        if honorFlags & 8 != 0 { return "James Beard semifinalist" }
        return nil
    }
    /// The chip for a James Beard line: the place's own honor, or a restaurateur (group) honor when that's the only one.
    var jamesBeardChip: String? { jamesBeardLabel ?? (jamesBeard != nil ? "James Beard (restaurateur)" : nil) }
    /// a hand-checked Delaware pick: the accent pins
    var isClassic: Bool { handChecked && !tags.isEmpty }
    var townLine: String { [city, cuisine].compactMap { $0 }.joined(separator: " · ") }
    var fullAddress: String {
        [address, [city, zip].compactMap { $0 }.joined(separator: " ")].compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: ", ")
    }

    /// Every place in the core file, built on all cores at once (each place's search text takes four normalizations).
    static func build(_ raw: [[String: Any]], file: DataFile) -> [Place] {
        var out = [Place?](repeating: nil, count: raw.count)
        let chunk = 2_000, chunks = (raw.count + chunk - 1) / chunk
        out.withUnsafeMutableBufferPointer { buf in
            let base = buf   // each chunk writes only its own slots
            DispatchQueue.concurrentPerform(iterations: chunks) { c in
                for k in (c * chunk)..<min(raw.count, (c + 1) * chunk) {
                    base[k] = PlaceRecord(raw[k]).map { Place($0, file: file) }
                }
            }
        }
        return out.compactMap { $0 }
    }

    init(_ r: PlaceRecord, file: DataFile) {
        let city = r.c.flatMap { $0 < file.cities.count ? file.cities[$0] : nil }
        let cuisine = r.cu < file.cuisines.count ? file.cuisines[r.cu] : "American & Other"
        let brand = r.b.flatMap { $0 < file.brands.count ? file.brands[$0] : nil }
        let county = r.co.flatMap { $0 < file.counties.count ? file.counties[$0] : nil }
        id = r.id
        name = r.n
        address = r.a
        self.city = city
        self.county = county
        zip = r.z
        if let la = r.la, let lo = r.lo { coordinate = CLLocationCoordinate2D(latitude: la, longitude: lo) } else { coordinate = nil }
        self.cuisine = cuisine
        self.brand = brand
        chainCount = r.ch ?? 1
        tier = Tier(rawValue: r.t) ?? .listing
        source = r.s < file.srcs.count ? file.srcs[r.s] : "meta"
        isVenue = r.v == 1
        isBar = r.bar == 1
        tags = PlaceTags(rawValue: r.g ?? 0)
        handChecked = r.hc == 1
        honorFlags = r.h ?? 0
        michelin = Michelin(rawValue: r.mi ?? 0) ?? .none
        iconicPoints = r.ip
        jamesBeard = r.jbf
        founded = r.f
        foundedNote = r.fn
        note = r.note
        dishes = r.dish
        seasonal = r.seas
        inspection = r.inspection
        // the dishes a hand-checked place serves are searchable too: "scrapple milford", "slippery dumplings seaford"
        searchText = " " + Search.normalize([r.n, r.aka, city, county, r.z, cuisine, brand, r.dish].compactMap { $0 }.joined(separator: " ")) + " "
            + Search.normalizeAddress(r.a ?? "") + " "
        nameText = " " + Search.normalize([r.n, brand].compactMap { $0 }.joined(separator: " ")) + " "
        sortKey = Search.normalize(r.n)
        location = coordinate.map { CLLocation(latitude: $0.latitude, longitude: $0.longitude) }
    }
}

/// The data's dates are calendar days ("2026-06-16"), not moments: read and shown in UTC, so no time zone can move one a day.
enum DayFormat {
    private static let utc = TimeZone(identifier: "UTC")!

    static func date(_ s: String?) -> Date? {
        guard let s, s.count >= 10 else { return nil }
        let parts = s.prefix(10).split(separator: "-").compactMap { Int($0) }
        guard parts.count == 3, (1...12).contains(parts[1]), (1...31).contains(parts[2]) else { return nil }
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = utc
        return cal.date(from: DateComponents(year: parts[0], month: parts[1], day: parts[2]))
    }

    /// "Jun 16, 2026" (in the reader's language); anything that isn't a date is shown as it is
    static func text(_ s: String?) -> String? {
        guard let s else { return nil }
        guard let d = date(s) else { return s }
        return d.formatted(Date.FormatStyle(date: .abbreviated, time: .omitted, timeZone: utc))
    }

    /// "Sep 2025"
    static func monthYear(_ s: String?) -> String? {
        guard let s else { return nil }
        guard let d = date(s) else { return s }
        return d.formatted(Date.FormatStyle(timeZone: utc).month(.abbreviated).year())
    }
}
