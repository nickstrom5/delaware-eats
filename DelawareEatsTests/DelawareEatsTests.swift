import XCTest
import CoreLocation
@testable import DelawareEats

@MainActor
final class DelawareEatsTests: XCTestCase {

    /// A tiny places.json with the same shape as Resources/places.json: the places and each one's detail in one file.
    private func sampleURL() throws -> URL {
        let json = """
        {"v":1,"generated":"2026-10-27","overture_release":"2026-10-21.0","dph_live":3483,"rev_licenses":2531,
         "inspections_through":{"dph":"2026-10-20"},
         "cities":["Rehoboth Beach","Wilmington","Bridgeville","Lewes","St. Georges","Dover"],
         "cuisines":["Pizza","Breakfast & Diner","Seafood","Italian","American & Other","Bar & Pub","BBQ"],
         "brands":["Grotto Pizza","Wawa"],"counties":["Sussex County","New Castle County","Kent County"],
         "srcs":["official","meta","AllThePlaces","DAC","research"],"itypes":["Routine","Follow-up","Complaint"],
         "sections":{"3-501.16":"Time/Temperature Control for Safety Food, Hot and Cold Holding","6-501.111":"Controlling Pests","2-102.12":"Certified Food Protection Manager"},
         "count":10,"count_restaurants":9,
         "calibration":{"Delaware":{"groups":{"meta_high":{"n":1908,"official":0.733}}},"Sussex County":{"groups":{"meta_high":{"n":544,"official":0.669}}}},
         "places":[
          {"id":"a","n":"Grotto Pizza","c":0,"co":0,"cu":0,"t":2,"s":1,"b":0,"ch":16,"hc":1,"g":130,"f":1960,"a":"36 Rehoboth Ave","z":"19971","la":38.7166,"lo":-75.0786,
           "dish":"boardwalk slice","in":[0,"2026-07-01","2026-07-01",0,0]},
          {"id":"b","n":"Scrapple Diner","c":2,"co":0,"cu":1,"t":1,"s":1,"hc":1,"g":1,"a":"100 Market St","la":38.742,"lo":-75.604,"in":[2,"2026-03-10","2026-03-18",0,1]},
          {"id":"c","n":"Crab House","c":3,"co":0,"cu":2,"t":2,"s":0,"hc":1,"g":4,"a":"200 Savannah Rd","la":38.77,"lo":-75.14,"in":[9,"2026-05-02","2026-05-02",9,0]},
          {"id":"d","n":"Some Grill","c":1,"co":1,"cu":4,"t":0,"s":1,"a":"300 N Market St","la":39.74,"lo":-75.55,"in":[5,"2025-12-01","2026-01-15",1,2]},
          {"id":"e","n":"Wawa","c":5,"co":2,"cu":4,"t":1,"s":1,"b":1,"ch":40,"v":1,"la":39.16,"lo":-75.52},
          {"id":"f","n":"Bardea Food & Drink","c":1,"co":1,"cu":3,"t":2,"s":1,"h":8,"jbf":"Best Chef: Mid-Atlantic semifinalist 2025 (Antimo DiMeo)","ip":20,"a":"620 N Market St","la":39.742,"lo":-75.548},
          {"id":"g","n":"Follow-up Only","c":1,"co":1,"cu":4,"t":2,"s":0,"la":39.745,"lo":-75.55,"in":[null,null,"2026-02-02",0,1]},
          {"id":"h","n":"Smokey Barbecue","c":5,"co":2,"cu":6,"t":1,"s":1,"la":39.16,"lo":-75.53},
          {"id":"i","n":"Canal Tavern","c":4,"co":1,"cu":5,"t":1,"s":1,"la":39.55,"lo":-75.65},
          {"id":"j","n":"Dogfish Brewpub","c":0,"co":0,"cu":5,"t":2,"s":1,"hc":1,"g":64,"a":"316 Rehoboth Ave","la":38.716,"lo":-75.085}
         ],
         "detail":{
          "a":{"lic":[["Delaware business license","2019700857","Retailer – Restaurant","2028-12-31"]],"ph":"(302) 227-3278","w":"grottopizza.com",
               "in":{"n":2,"h":[["2026-07-01",0,0,[]],["2025-08-12",0,2,["3-501.16","6-501.111"]]]}},
          "c":{"w":"javascript:alert(1)","in":{"n":1,"h":[["2026-05-02",0,9,["2-102.12"]]]}},
          "zz":{"ph":"(302) 000-0000"}
         }}
        """
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("de-test-\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let url = dir.appendingPathComponent("places.json")
        try json.data(using: .utf8)!.write(to: url)
        return url
    }

    private func sampleModel() async throws -> AppModel {
        let model = AppModel(defaults: UserDefaults(suiteName: "test-\(UUID().uuidString)")!)
        await model.load(from: try sampleURL())
        XCTAssertTrue(model.isLoaded, model.loadError ?? "")
        return model
    }

    func testDecodesAndHidesNonRestaurantsByDefault() async throws {
        let m = try await sampleModel()
        XCTAssertEqual(m.places.count, 10)
        XCTAssertEqual(m.restaurantCount, 9)
        XCTAssertFalse(m.list(.all, sort: .name, search: "", here: nil).contains { $0.name == "Wawa" }, "a convenience-store counter is hidden by default")
        m.filters.includeNonRestaurants = true
        XCTAssertTrue(m.list(.all, sort: .name, search: "", here: nil).contains { $0.name == "Wawa" })
    }

    func testGuidesListOnlyWhatTheyPromise() async throws {
        let m = try await sampleModel()
        XCTAssertEqual(m.list(.boardwalk, sort: .name, search: "", here: nil).map(\.name), ["Grotto Pizza"])
        XCTAssertEqual(m.list(.scrapple, sort: .name, search: "", here: nil).map(\.name), ["Scrapple Diner"])
        XCTAssertEqual(m.list(.crab, sort: .name, search: "", here: nil).map(\.name), ["Crab House"])
        XCTAssertEqual(m.list(.brewpub, sort: .name, search: "", here: nil).map(\.name), ["Dogfish Brewpub"])
        XCTAssertEqual(m.list(.oldest, sort: .oldest, search: "", here: nil).map(\.name), ["Grotto Pizza"])
        XCTAssertEqual(m.list(.honors, sort: .iconic, search: "", here: nil).map(\.name), ["Bardea Food & Drink"])
        XCTAssertEqual(m.count(.dumplings), 0)
    }

    /// DPH publishes no grade: the list sorts by the Food Code sections cited at the latest routine inspection, and a place DPH saw only
    /// on a follow-up or complaint visit has no routine count to rank.
    func testInspectionsAreDPHsOwnCounts() async throws {
        let m = try await sampleModel()
        let most = m.list(.inspections, sort: .mostCited, search: "", here: nil)
        XCTAssertEqual(most.map(\.name), ["Crab House", "Some Grill", "Scrapple Diner", "Grotto Pizza"], "most sections first; no routine, not listed")
        XCTAssertEqual(m.list(.inspections, sort: .fewestCited, search: "", here: nil).first?.name, "Grotto Pizza")
        XCTAssertEqual(m.list(.inspections, sort: .recent, search: "", here: nil).first?.name, "Grotto Pizza")
        let g = try XCTUnwrap(m.place(id: "g")?.inspection)
        XCTAssertNil(g.routineCount); XCTAssertTrue(g.hasLaterVisit)
        XCTAssertFalse(m.list(.inspections, sort: .recent, search: "", here: nil).contains { $0.id == "g" })
        let d = try XCTUnwrap(m.place(id: "d")?.inspection)
        XCTAssertEqual(d.routineCount, 5); XCTAssertTrue(d.hasLaterVisit, "a complaint visit after the routine one is shown with it")
        XCTAssertEqual(m.visitType(d.lastType), "Complaint")
        XCTAssertFalse(try XCTUnwrap(m.place(id: "a")?.inspection).hasLaterVisit)
        XCTAssertEqual(m.dphThrough, "2026-10-20")
    }

    func testDatesAreCalendarDays() {
        var utc = Calendar(identifier: .gregorian)
        utc.timeZone = TimeZone(identifier: "UTC")!
        let d = DayFormat.date("2026-06-16")!
        XCTAssertEqual(utc.dateComponents([.year, .month, .day], from: d), DateComponents(year: 2026, month: 6, day: 16))
        XCTAssertTrue(DayFormat.monthYear("2025-09-01")!.contains("2025"))
        XCTAssertNil(DayFormat.date("2026-13-01"))
        XCTAssertEqual(DayFormat.text("soon"), "soon", "a value that isn't a date is shown as it is")
    }

    func testDetailComesFromTheOneFile() async throws {
        let m = try await sampleModel()
        let v = await m.detail(for: m.place(id: "a")!)
        XCTAssertEqual(v?.licenses.first?.source, "Delaware business license")
        XCTAssertEqual(v?.licenses.first?.id, "2019700857")
        XCTAssertEqual(v?.licenses.first?.validThrough, "2028-12-31", "a license shows the date it's valid through")
        XCTAssertEqual(v?.website?.absoluteString, "https://grottopizza.com", "a bare host gets https://")
        XCTAssertEqual(v?.inspection?.visits.count, 2)
        XCTAssertEqual(v?.inspection?.visits.last?.codes, ["3-501.16", "6-501.111"])
        XCTAssertEqual(m.sectionTitle("6-501.111"), "Controlling Pests", "the section's title, as DPH publishes it")
        let crab = await m.detail(for: m.place(id: "c")!)
        XCTAssertNil(crab?.website, "a javascript: link never becomes a website button")
        let none = await m.detail(for: m.place(id: "h")!)
        XCTAssertNil(none, "a place with no detail record reads as no detail, not a crash")
        // the layout check reads the same file the same way (a detail record for an unknown id is ignored, never shown)
        let summary = try DataLayout.app.read(try sampleURL().deletingLastPathComponent())
        XCTAssertEqual(summary.places, 10); XCTAssertEqual(summary.generated, "2026-10-27")
    }

    func testSearchWordStartsTownsAndGuides() async throws {
        let m = try await sampleModel()
        XCTAssertEqual(m.list(.all, sort: .name, search: "grotto reh", here: nil).map(\.name), ["Grotto Pizza"])
        XCTAssertEqual(m.list(.all, sort: .name, search: "lewes", here: nil).map(\.name), ["Crab House"], "a town narrows to it")
        XCTAssertEqual(m.list(.all, sort: .name, search: "boardwalk slice", here: nil).map(\.name), ["Grotto Pizza"], "a dish finds who serves it")
        XCTAssertEqual(m.list(.all, sort: .name, search: "🍕", here: nil), [], "an emoji finds nothing, not everything")
        XCTAssertEqual(m.list(.all, sort: .name, search: "scrapple", here: nil).map(\.name), ["Scrapple Diner"], "a guide phrase means the guide")
        XCTAssertEqual(m.list(.all, sort: .name, search: "saint georges", here: nil).map(\.name), ["Canal Tavern"], "St. and Saint are one town")
        XCTAssertEqual(Set(m.list(.all, sort: .name, search: "bbq", here: nil).map(\.name)), ["Smokey Barbecue"])
        XCTAssertEqual(m.list(.all, sort: .name, search: "barbecue", here: nil).map(\.name), ["Smokey Barbecue"], "barbecue and BBQ are one word")
        XCTAssertEqual(m.list(.all, sort: .name, search: "n market", here: nil).map(\.name).sorted(), ["Bardea Food & Drink", "Some Grill"])
    }

    /// Letters folding can't strip an accent from still match their plain spelling.
    func testSearchFoldsLettersWithoutAccents() {
        XCTAssertEqual(Search.normalize("Ørchard Bar & Table"), "orchard bar and table")
        XCTAssertEqual(Search.normalize("Brutø Æble Phở Đô Łódź Straße"), "bruto aeble pho do lodz strasse")
    }

    func testOutsideDelawareUsesTheOutline() {
        func inside(_ la: Double, _ lo: Double) -> Bool { DelawareOutline.contains(CLLocationCoordinate2D(latitude: la, longitude: lo)) }
        XCTAssertTrue(inside(39.745, -75.547), "Wilmington"); XCTAssertTrue(inside(39.158, -75.524), "Dover"); XCTAssertTrue(inside(38.717, -75.079), "Rehoboth Beach")
        XCTAssertTrue(inside(38.463, -75.054), "Fenwick Island"); XCTAssertTrue(inside(38.457, -75.577), "Delmar"); XCTAssertTrue(inside(39.807, -75.452), "Claymont")
        XCTAssertTrue(inside(38.776, -75.140), "Lewes"); XCTAssertTrue(inside(39.683, -75.750), "Newark")
        XCTAssertFalse(inside(39.952, -75.165), "Philadelphia"); XCTAssertFalse(inside(39.607, -75.833), "Elkton, Md."); XCTAssertFalse(inside(38.366, -75.599), "Salisbury, Md.")
        XCTAssertFalse(inside(38.336, -75.085), "Ocean City, Md."); XCTAssertFalse(inside(38.935, -74.906), "Cape May, N.J.")
        XCTAssertFalse(inside(37.33, -122.03), "Cupertino")
    }

    func testMatchRatesComeFromTheStatewideList() async throws {
        let m = try await sampleModel()
        XCTAssertNil(m.matchRate(for: m.place(id: "a")!), "an official record needs no listing rate")
        XCTAssertEqual(m.matchRate(for: m.place(id: "b")!), "73%", "the statewide share, not a county's")
    }

    func testBundledData() async throws {
        let m = AppModel(defaults: UserDefaults(suiteName: "bundle-\(UUID().uuidString)")!)
        await m.load()
        XCTAssertTrue(m.isLoaded, m.loadError ?? "")
        XCTAssertGreaterThan(m.restaurantCount, 2_400)
        XCTAssertGreaterThan(m.count(.inspections), 1_500)
        XCTAssertGreaterThan(m.licensedCount, 2_000, "restaurants matched to a DPH establishment or a Revenue license")
        XCTAssertEqual(Set(m.places.map(\.id)).count, m.places.count, "ids are unique")
        for g in Guide.allCases where g.tag != nil {
            XCTAssertTrue(m.places.filter(g.includes).allSatisfy(\.handChecked), "\(g.title) lists only hand-checked places")
        }
        let through = try XCTUnwrap(m.dphThrough)
        XCTAssertTrue(m.places.allSatisfy { p in p.inspection.map { $0.lastDate <= through && ($0.routineDate ?? "") <= through && ($0.routineCount ?? 0) >= 0
                      && $0.lastCount >= 0 } ?? true }, "no inspection after the records-through date (DPH's feed carries future dates)")
        XCTAssertTrue(m.places.allSatisfy { $0.michelin == .none }, "Delaware has no MICHELIN Guide")
        XCTAssertTrue(m.places.allSatisfy { $0.coordinate.map { DelawareOutline.contains($0) } ?? true }, "every place is inside Delaware")
        // the searches the App Store description and the App Review notes promise (scripts/make-listing.py)
        XCTAssertTrue(m.list(.all, sort: .name, search: "scrapple smyrna", here: nil).contains { $0.name == "Helen's Sausage House" },
                      "\"scrapple smyrna\" finds Helen's Sausage House")
        XCTAssertGreaterThan(m.list(.all, sort: .name, search: "italian wilmington", here: nil).count, 10, "\"italian wilmington\" finds Wilmington's Italian places")
    }

    /// No Google-derived number ships: no key anywhere in the bundled data names a rating, review, price level, Google listing or the
    /// 2021 snapshot (Oregon and South Carolina once shipped calibration.*.google21_open).
    func testNoGoogleDataInTheBundle() throws {
        let files = TrackingParams.bundledJSON()
        XCTAssertFalse(files.isEmpty)
        for url in files {
            let obj = try JSONSerialization.jsonObject(with: Data(contentsOf: url))
            XCTAssertEqual(NoGoogle.keys(in: obj), [], "\(url.lastPathComponent) has Google-derived keys")
        }
    }

    func testNoGoogleGuardCatchesABrokenCopy() throws {
        let raw = try Data(contentsOf: Bundle.main.url(forResource: "places", withExtension: "json")!)
        var file = try XCTUnwrap(JSONSerialization.jsonObject(with: raw) as? [String: Any])
        var cal = (file["calibration"] as? [String: Any]) ?? [:]
        cal["Delaware"] = ["groups": ["meta_high": ["n": 1, "official": 0.7, "google21_open": 0.9]]]
        file["calibration"] = cal
        var places = try XCTUnwrap(file["places"] as? [[String: Any]])
        places[0]["rating"] = 4.5
        file["places"] = places
        XCTAssertEqual(Set(NoGoogle.keys(in: file)), ["google21_open", "rating"])
    }

    /// The screenshots' places are in the data, and none is shown with a later follow-up or complaint visit.
    /// Woodside Farm Creamery matched DPH's record for its farm stand (a non-food establishment, so no inspections shown) and no Revenue
    /// license: its "Official record" once said "Delaware business license" above a "Business license — (none matched)" row.
    func testOfficialRecordNamesTheSourceThatMatched() {
        XCTAssertEqual(PlaceDetailView.officialRecord(inspected: true, licensed: true), "Division of Public Health")
        XCTAssertEqual(PlaceDetailView.officialRecord(inspected: false, licensed: true), "Delaware business license")
        XCTAssertEqual(PlaceDetailView.officialRecord(inspected: false, licensed: false), "Division of Public Health")
    }

    func testScreenshotPicksExist() async throws {
        let m = AppModel(defaults: UserDefaults(suiteName: "shots-\(UUID().uuidString)")!)
        await m.load()
        for (n, town) in [ScreenshotMode.detailPick, ScreenshotMode.padPick, ScreenshotMode.crabPick, ScreenshotMode.scrapplePick,
                           ScreenshotMode.creameryPick, ScreenshotMode.honorPick]
            + ScreenshotMode.savedPicks {
            let p = try XCTUnwrap(m.places.first { $0.name == n && $0.city == town }, "\(n) is in the data")
            XCTAssertFalse(p.inspection?.hasLaterVisit ?? false, "\(n) has a follow-up or complaint visit after its routine inspection")
        }
    }

    /// Stable ids: md5(name + ~100 m cell)[:12], never a row number; the bundled detail names only bundled places' ids.
    func testIdsAndBundledDetail() async throws {
        let m = AppModel(defaults: UserDefaults(suiteName: "ids-\(UUID().uuidString)")!)
        await m.load()
        XCTAssertTrue(m.places.allSatisfy { $0.id.count >= 12 && $0.id.prefix(12).allSatisfy(\.isHexDigit) && $0.id.dropFirst(12).allSatisfy { $0 == "x" } })
        let ids = Set(m.places.map(\.id))
        let (_, _, details) = try AppModel.readAll(Bundle.main.url(forResource: "places", withExtension: "json")!)
        XCTAssertTrue(Set(details.keys).isSubset(of: ids), "detail ids are place ids")
        XCTAssertGreaterThan(details.values.filter { $0.licenses.contains { $0.source == "Delaware business license" && $0.validThrough != nil } }.count, 1_000,
                             "licensed places carry their Revenue license and its valid-through date")
        XCTAssertGreaterThan(details.values.filter { !($0.inspection?.visits.isEmpty ?? true) }.count, 1_500, "inspected places carry their history")
    }

    func testBundledDataGuards() async throws {
        let m = AppModel(defaults: UserDefaults(suiteName: "guards-\(UUID().uuidString)")!)
        await m.load()
        XCTAssertTrue(m.isLoaded, m.loadError ?? "")
        XCTAssertEqual(DataGuards.adultVenues(m.places), [], "no strip club under its name")
        XCTAssertEqual(DataGuards.badWebsites(try DataGuards.bundledLinks(m.places)), [], "no directory, Google or news page as a restaurant's website")
        XCTAssertEqual(DataGuards.badNames(m.places), [], "no visible name ending in \u{201C} the\u{201D} or \u{201C} of\u{201D}, or just \u{201C}The\u{201D}")
        XCTAssertEqual(DataGuards.legalNames(m.places), [], "no license holder entity name (\u{201C}… LLC\u{201D}) shown as a place's name")
        XCTAssertEqual(DataGuards.nonRestaurants(m.places), [], "no nail salon, senior home, gun store or gas station among the restaurants")
        XCTAssertEqual(DataGuards.dphClosedNames(m.places), [], "no DPH \u{201C}(Closed)\u{201D} suffix or cut-off name shown")
        XCTAssertEqual(DataGuards.malformedWebsites(try DataGuards.bundledWebsiteStrings()), [], "every website is one link with no spaces, not a map link")
    }

    /// Each guard above fires on a copy of the bundled data broken the way QA found it elsewhere: a guard that can't fail guards nothing.
    func testGuardsCatchABrokenCopy() async throws {
        let raw = try Data(contentsOf: Bundle.main.url(forResource: "places", withExtension: "json")!)
        var file = try XCTUnwrap(JSONSerialization.jsonObject(with: raw) as? [String: Any])
        var places = try XCTUnwrap(file["places"] as? [[String: Any]])
        let idx = places.indices.filter { places[$0]["v"] == nil }.prefix(7).map { $0 }
        places[idx[2]]["n"] = "Larry Flynt's Hustler Club"
        places[idx[3]]["n"] = "Kitchen the"
        places[idx[4]]["n"] = "FIRST STATE HOSPITALITY GROUP LLC"
        places[idx[5]]["n"] = "Tipsy Nails & Spa"
        places[idx[6]]["n"] = "Bahama Breeze (Closed)"
        file["places"] = places
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("places-broken.json")
        try JSONSerialization.data(withJSONObject: file).write(to: url)
        let m = AppModel(defaults: UserDefaults(suiteName: "broken-\(UUID().uuidString)")!)
        await m.load(from: url)
        XCTAssertTrue(m.isLoaded, m.loadError ?? "")
        let id = idx.map { places[$0]["id"] as? String }
        func caught(_ found: [String], _ i: Int, _ what: String) {
            XCTAssertTrue(found.contains { $0.contains("[\(id[i] ?? "?")]") }, "the guard missed \(what)")
        }
        let links = [(name: "A", id: "x1", url: "https://www.yelp.com/biz/some-place"), (name: "B", id: "x2", url: "https://www.delawareonline.com/story/entertainment/dining/"),
                     (name: "C", id: "x3", url: "https://smart.com/menu")]
        XCTAssertEqual(DataGuards.badWebsites(links).count, 2, "the guard catches a Yelp page and a news story, and not smart.com")
        let shapes = [(name: "D", id: "x4", url: "https://a.example/menu https://b.example"), (name: "E", id: "x5", url: "https://a.examplehttps://b.example/"),
                      (name: "F", id: "x6", url: "https://maps.app.goo.gl/AbC123"), (name: "G", id: "x7", url: "https://www.google.com/maps/place/Some+Grill"),
                      (name: "H", id: "x8", url: "https://maps.apple.com/?q=Some+Grill"),
                      (name: "I", id: "x9", url: "https://order.example.com/r/51?next=https://order.example.com/menu"), (name: "J", id: "x10", url: "https://mapleleafgrill.com/")]
        XCTAssertEqual(DataGuards.malformedWebsites(shapes).map { String($0.prefix(1)) }, ["D", "E", "F", "G", "H"],
                       "two links in one, a space, and map links are caught; a link inside a query and a maple-named site are not")
        caught(DataGuards.adultVenues(m.places), 2, "a strip club")
        caught(DataGuards.badNames(m.places), 3, "\u{201C}Kitchen the\u{201D}")
        caught(DataGuards.legalNames(m.places), 4, "a license holder's entity name")
        caught(DataGuards.nonRestaurants(m.places), 5, "a nail salon shown as a restaurant")
        caught(DataGuards.dphClosedNames(m.places), 6, "a DPH \u{201C}(Closed)\u{201D} name")
    }
}

/// Keys that would carry Google-derived data: ratings, reviews, price levels, Google listing ids, the 2021 snapshot's flags.
enum NoGoogle {
    static let pattern = try! NSRegularExpression(pattern: #"google|rating|review|gmap|price|in21|closed21"#, options: [.caseInsensitive])

    static func keys(in obj: Any) -> [String] {
        var out: [String] = []
        func walk(_ o: Any) {
            if let d = o as? [String: Any] {
                for (k, v) in d {
                    if pattern.firstMatch(in: k, range: NSRange(k.startIndex..., in: k)) != nil { out.append(k) }
                    walk(v)
                }
            } else if let a = o as? [Any] {
                for v in a { walk(v) }
            }
        }
        walk(obj)
        return Array(Set(out)).sorted()
    }
}

/// Checks on the bundled data, written as functions so testGuardsCatchABrokenCopy can prove each one fires.
enum DataGuards {
    /// directories, Google and news sites: matched on the link's host, so "smart.com" isn't "rt.com"
    static let badHosts = #"^https?://([^/?#]*\.)?(yelp\.com|business\.site|google\.com|groupon\.com|yellowpages\.com|tripadvisor\.com|delawareonline\.com|delawarelive\.com|townsquaredelaware\.com|capegazette\.com|coastalpoint\.com|wdel\.com|wboc\.com|wmdt\.com|visitdelaware\.com|eater\.com|rt\.com)([:/?#]|$)"#

    static func badWebsites(_ links: [(name: String, id: String, url: String)]) -> [String] {
        links.compactMap { l in
            guard l.url.range(of: badHosts, options: [.regularExpression, .caseInsensitive]) != nil else { return nil }
            return "\(l.name) [\(l.id)]: \(l.url)"
        }
    }

    /// a map link, by host (and Google's /maps path), never a restaurant's own website
    static let mapLink = #"^https?://([^/?#]*\.)?(maps\.google\.[a-z.]+([:/?#]|$)|google\.[a-z.]+/maps([/?#]|$)|goo\.gl/maps([/?#]|$)|maps\.app\.goo\.gl([:/?#]|$)|maps\.apple\.com([:/?#]|$)|bing\.com/maps([/?#]|$)|waze\.com([:/?#]|$)|mapquest\.com([:/?#]|$))"#

    /// QA 2026-10-28 (P1): a website is one http(s) link with no space in it and isn't a map link. A second scheme not right after "="
    /// (a link inside a query is fine) means two links were glued together.
    static func malformedWebsites(_ links: [(name: String, id: String, url: String)]) -> [String] {
        links.compactMap { l in
            let u = l.url
            let one = u.range(of: #"^https?://\S+$"#, options: [.regularExpression, .caseInsensitive]) != nil
                && u.range(of: #"(?i).(?<![=%])https?://"#, options: .regularExpression) == nil
            guard !one || u.range(of: mapLink, options: [.regularExpression, .caseInsensitive]) != nil else { return nil }
            return "\(l.name) [\(l.id)]: \(u)"
        }
    }

    /// every website string in the bundled file as stored, before URL parsing could hide a space or a second link
    static func bundledWebsiteStrings() throws -> [(name: String, id: String, url: String)] {
        let file = try JSONSerialization.jsonObject(with: Data(contentsOf: Bundle.main.url(forResource: "places", withExtension: "json")!)) as? [String: Any]
        let names = Dictionary(((file?["places"] as? [[String: Any]]) ?? []).compactMap { p in (p["id"] as? String).map { ($0, p["n"] as? String ?? "?") } },
                               uniquingKeysWith: { a, _ in a })
        return ((file?["detail"] as? [String: [String: Any]]) ?? [:]).compactMap { id, d in (d["w"] as? String).map { (names[id] ?? "?", id, $0) } }
    }

    /// every website link in the bundled detail, with its place's name
    static func bundledLinks(_ places: [Place]) throws -> [(name: String, id: String, url: String)] {
        let names = Dictionary(places.map { ($0.id, $0.name) }, uniquingKeysWith: { a, _ in a })
        let (_, _, details) = try AppModel.readAll(Bundle.main.url(forResource: "places", withExtension: "json")!)
        return details.compactMap { id, d in d.website.map { (names[id] ?? "?", id, $0.absoluteString) } }
    }

    static let adultNames = #"gentlem[ae]n['’]?s club|strip club|exotic dancer|\bmen['’]?s club|rick['’]?s cabaret|xtc cabaret|baby dolls|spearmint rhino|bikini bar|pt['’]?s showclub|showgirls|centerfolds|treasures? gentlem|deja ?vu showgirls|hustler club|penthouse club"#

    static func adultVenues(_ places: [Place]) -> [String] {
        places.filter { $0.name.range(of: adultNames, options: [.regularExpression, .caseInsensitive]) != nil }.map { "\($0.name) [\($0.id)]" }
    }

    /// a name cut off after "the" or "of" ("Kitchen the", "Wines of") or nothing but "The", among the places shown by default
    static func badNames(_ places: [Place]) -> [String] {
        places.filter { p in
            let n = p.name.trimmingCharacters(in: .whitespaces).lowercased()
            return !p.isVenue && (n.hasSuffix(" the") || n.hasSuffix(" of") || n == "the")
        }.map { "\($0.name) [\($0.id)]" }
    }

    /// a license holder is never shown; a business name that's still a legal entity shouldn't be either
    static let legalSuffix = #"\b(llc|l\.l\.c|inc|corp|corporation)\.?$"#

    static func legalNames(_ places: [Place]) -> [String] {
        places.filter { !$0.isVenue && $0.name.range(of: legalSuffix, options: [.regularExpression, .caseInsensitive]) != nil }
            .map { "\($0.name) [\($0.id)]" }
    }

    /// businesses that aren't places to eat, among the places shown by default
    static let nonRestaurantNames = #"\bnails?\b|assisted living|gun (?:club|range|shop|store)|shooting range|firearms|petroleum|\bauto (?:repair|parts)\b"#

    static func nonRestaurants(_ places: [Place]) -> [String] {
        places.filter { !$0.isVenue && $0.name.range(of: nonRestaurantNames, options: [.regularExpression, .caseInsensitive]) != nil }
            .map { "\($0.name) [\($0.id)]" }
    }

    /// DPH's "(Closed)" suffix, its cut-off forms, a mobile-unit tag or a "DBA - legal entity" tail left in a shown name
    static let dphLeftovers = #"\(\s*clos|\((?:MOB|CWOP)\)|\s-\s.*\b(?:llc|inc)\b"#

    static func dphClosedNames(_ places: [Place]) -> [String] {
        places.filter { $0.name.range(of: dphLeftovers, options: [.regularExpression, .caseInsensitive]) != nil }.map { "\($0.name) [\($0.id)]" }
    }
}

/// pipeline/website_blocklist.json (hacked, taken-over, expired or another business's sites, confirmed by hand in the link sweeps):
/// no link on it may ship in any field of any JSON file the app bundles. The 2026-10-19 QA found the export had only filtered the
/// website field, or nothing, so hijacked links were still in the bundle. Read from the repo, so a new entry needs no code change.
final class LinkBlocklistTests: XCTestCase {
    func testNoBlocklistedLinkInBundledData() throws {
        let entries = try LinkBlocklist.entries()
        XCTAssertFalse(entries.isEmpty, "the blocklist is missing or empty")
        let files = LinkBlocklist.bundledJSON()
        XCTAssertFalse(files.isEmpty, "no bundled JSON found")
        var hits: [String] = []
        for url in files {
            let text = try String(contentsOf: url, encoding: .utf8)
            hits += LinkBlocklist.hits(in: text, entries).map { "\(url.lastPathComponent): \($0)" }
        }
        XCTAssertEqual(hits, [], "blocklisted links in the app's bundled data")
    }

    /// The guard fires on a copy of the bundled data broken three ways: a blocklisted domain, its subdomain, and a "url" entry.
    func testBlocklistGuardCatchesABrokenCopy() throws {
        let entries = try LinkBlocklist.entries()
        let file = try XCTUnwrap(LinkBlocklist.bundledJSON().max { (try? $0.resourceValues(forKeys: [.fileSizeKey]).fileSize ?? 0) ?? 0 < (try? $1.resourceValues(forKeys: [.fileSizeKey]).fileSize ?? 0) ?? 0 })
        let text = try String(contentsOf: file, encoding: .utf8)
        let domain = try XCTUnwrap(entries.first { ($0["match"] as? String ?? "domain") == "domain" }?["domain"] as? String)
        let fake: [[String: Any]] = entries + [["match": "url", "url": "https://example.org/hacked-page"]]
        let before = LinkBlocklist.hits(in: text, fake).count
        let broken = text + "{\"w\":\"https://www.\(domain)/menu\"}{\"src\":\"http://shop.\(domain)/\"}{\"w\":\"https://example.org/hacked-page/\"}"
        XCTAssertEqual(LinkBlocklist.hits(in: broken, fake).count, before + 3, "a domain, a subdomain and a url entry are all caught")
        XCTAssertEqual(LinkBlocklist.hits(in: "{\"w\":\"https://not\(domain)/\"}", entries), [], "a host that only ends with the domain's letters isn't it")
    }
}

enum LinkBlocklist {
    static func entries() throws -> [[String: Any]] {
        let url = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("pipeline/website_blocklist.json")
        return try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [[String: Any]])
    }

    /// every .json file in the app bundle, subfolders included
    static func bundledJSON() -> [URL] {
        let root = Bundle.main.bundleURL
        let all = FileManager.default.enumerator(at: root, includingPropertiesForKeys: nil)?.allObjects as? [URL] ?? []
        return all.filter { $0.pathExtension == "json" && !$0.path.contains("/PlugIns/") }
    }

    private static func host(_ u: URLComponents) -> String {
        var h = (u.host ?? "").lowercased()
        if h.hasSuffix(".") { h.removeLast() }
        return h.hasPrefix("www.") ? String(h.dropFirst(4)) : h
    }

    private static func trimmedPath(_ p: String) -> String { p.hasSuffix("/") ? String(p.dropLast()) : p }

    /// the links in a JSON text that an entry covers: a "domain" entry its domain and subdomains, a "url" entry that page only
    static func hits(in text: String, _ entries: [[String: Any]]) -> [String] {
        let t = text.replacingOccurrences(of: "\\/", with: "/")
        let rx = try! NSRegularExpression(pattern: #"https?://[^"\s\\]+"#, options: [.caseInsensitive])
        return rx.matches(in: t, range: NSRange(t.startIndex..., in: t)).compactMap { m -> String? in
            let s = String(t[Range(m.range, in: t)!])
            guard let u = URLComponents(string: s) else { return nil }
            let h = host(u)
            for e in entries {
                if (e["match"] as? String ?? "domain") == "url" {
                    guard let v = URLComponents(string: e["url"] as? String ?? "") else { continue }
                    if !h.isEmpty && h == host(v) && trimmedPath(u.path) == trimmedPath(v.path) { return s }
                } else {
                    var d = (e["domain"] as? String ?? "").lowercased()
                    if let r = d.range(of: "://") { d = String(d[r.upperBound...]) }
                    d = String(d.split(separator: "/").first ?? "")
                    if d.hasPrefix("www.") { d = String(d.dropFirst(4)) }
                    if !d.isEmpty && (h == d || h.hasSuffix("." + d)) { return s }
                }
            }
            return nil
        }
    }
}

/// QA 2026-10-19, P1 3a: the support address is nick@eatsranked.com (Nick, 2026-10-12). The old Gmail address must not come back
/// anywhere in the app's source or bundled files.
final class SupportEmailTests: XCTestCase {
    func testSupportEmailIsEatsRanked() {
        XCTAssertEqual(Links.supportEmail, "nick@eatsranked.com")
    }

    func testNoGmailInAppSource() throws {
        let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("DelawareEats")
        XCTAssertGreaterThan(SupportEmailScan.textFiles(under: root).count, 5, "the app's source folder wasn't found")
        XCTAssertEqual(SupportEmailScan.hits(under: root), [], "the app's source still has a Gmail address")
    }

    /// The guard fires on a broken copy: a folder with one planted Gmail address.
    func testGmailGuardCatchesABrokenCopy() throws {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: dir.appendingPathComponent("App"), withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: dir) }
        try "static let supportEmail = \"someone@GMAIL.com\"\n".write(to: dir.appendingPathComponent("App/Links.swift"), atomically: true, encoding: .utf8)
        try "{\"ok\": \"nick@eatsranked.com\"}".write(to: dir.appendingPathComponent("App/data.json"), atomically: true, encoding: .utf8)
        XCTAssertEqual(SupportEmailScan.hits(under: dir), ["App/Links.swift"])
    }
}

enum SupportEmailScan {
    static let textExtensions: Set<String> = ["swift", "plist", "json", "strings", "xcstrings", "xcprivacy", "md", "txt", "html", "entitlements"]

    static func textFiles(under root: URL) -> [URL] {
        let all = FileManager.default.enumerator(at: root, includingPropertiesForKeys: nil)?.allObjects as? [URL] ?? []
        return all.filter { textExtensions.contains($0.pathExtension.lowercased()) }
    }

    /// paths (relative to root) of text files that mention gmail.com, in any case
    static func hits(under root: URL) -> [String] {
        let base = root.resolvingSymlinksInPath().path + "/"
        return textFiles(under: root).compactMap { url in
            guard let text = try? String(contentsOf: url, encoding: .utf8),
                  text.range(of: "gmail.com", options: .caseInsensitive) != nil else { return nil }
            return url.resolvingSymlinksInPath().path.replacingOccurrences(of: base, with: "")
        }.sorted()
    }
}

/// QA 2026-10-19, P1 #13: outbound links ship without tracking tags (ref=google, referrer=google_food_ordering, cn_channel, utm_* …).
/// pipeline/tracking_params.py strips them in the export; these are the same rules.
final class TrackingParamTests: XCTestCase {
    func testNoTrackingParametersInBundledLinks() throws {
        let files = TrackingParams.bundledJSON()
        XCTAssertFalse(files.isEmpty, "no bundled JSON found")
        var hits: [String] = []
        for url in files {
            let text = try String(contentsOf: url, encoding: .utf8)
            hits += TrackingParams.tracked(in: text).map { "\(url.lastPathComponent): \($0)" }
        }
        XCTAssertEqual(hits, [], "links with tracking parameters in the app's bundled data")
    }

    /// The guard fires on a broken copy (four kinds of tracking tag, one in escaped JSON) and leaves a store's own parameters alone.
    func testTrackingGuardCatchesABrokenCopy() {
        let broken = #"[{"w":"https:\/\/places.example.com\/menu?ref=google"},{"w":"https://a.example/?utm_source=gmb&store=4"},"#
            + #"{"w":"https://b.example/x?referrer=google_food_ordering"},{"w":"https://c.example/order/1?cn_channel=cn_google"},"#
            // QA 2026-10-28: after "#", inside a route's own query, written into the path, without a scheme, Klaviyo's _kx
            + #"{"w":"https://d.example/las-vegas/#utm_source=rest_of_network"},{"w":"https://e.example/#/menu?utm_medium=listing&table=4"},"#
            + #"{"w":"https://f.example/alpharetta/utm_source=Facebook&utm_medium=BusinessListing"},{"w":"instagram.com/somewhere?igshid=abc"},"#
            + #"{"w":"https://g.example/shop?_kx=a1b2"}]"#
        XCTAssertEqual(TrackingParams.tracked(in: broken).count, 9)
        let clean = #"[{"w":"https://order.example.com/menu?restaurantId=51&location=7"},{"w":"https://shop.example.com/?cid=12&ref=gs"},"#
            + #"{"w":"https://h.example/#/menu?table=4"},{"w":"https://i.example/page#about"},{"w":"facebook.com/someplace"},"#
            + #"{"w":"https://j.example/store/id=55/menu"}]"#
        XCTAssertEqual(TrackingParams.tracked(in: clean), [])
    }
}

enum TrackingParams {
    /// tracking by name, whatever the value
    static let keys = try! NSRegularExpression(pattern: #"^(?:utm[_-].*|gclid|gbraid|wbraid|dclid|fbclid|msclkid|mc_cid|mc_eid|_ga|_gl|_kx|igsh|"#
        + #"igshid|mibextid|srsltid|cn_channel|y_source|rwg_token|olonwp|ost_redirect_attribution|cmpid|yext_?.*)$"#, options: [.caseInsensitive])
    /// tracking only with these values
    static let values: [String: String] = ["ref": #"^(?:google|gmb|gbp|yext|bookmarks)\b"#, "referrer": "^google",
                                           "source": #"^(?:google|gmb|gbp|yext)\b"#, "cid": "^RF:YXT", "cmp": "^OKC-"]

    /// every .json file in the app bundle, subfolders included
    static func bundledJSON() -> [URL] {
        let all = FileManager.default.enumerator(at: Bundle.main.bundleURL, includingPropertiesForKeys: nil)?.allObjects as? [URL] ?? []
        return all.filter { $0.pathExtension == "json" && !$0.path.contains("/PlugIns/") }
    }

    static func isTracking(_ key: String, _ value: String) -> Bool {
        let k = key.trimmingCharacters(in: .whitespaces)
        if keys.firstMatch(in: k, range: NSRange(k.startIndex..., in: k)) != nil { return true }
        guard let pattern = values[k.lowercased()] else { return false }
        return value.trimmingCharacters(in: .whitespaces).range(of: pattern, options: [.regularExpression, .caseInsensitive]) != nil
    }

    /// links in a JSON text that still carry a tracking parameter, as pipeline/tracking_params.py finds them: in the query, after "#"
    /// (Yext's "…/las-vegas/#utm_source=…", or a route's own query "#/menu?utm_source=…"), written into the path
    /// ("…/alpharetta/utm_source=Facebook&utm_medium=BusinessListing"), and in links stored without a scheme ("instagram.com/x?igshid=…")
    static func tracked(in text: String) -> [String] {
        let t = text.replacingOccurrences(of: "\\/", with: "/").replacingOccurrences(of: "&amp;", with: "&")
        let rx = try! NSRegularExpression(pattern: #"(?i)https?://[^\s"'<>\\]+|(?<![\w/.:@-])(?:[a-z0-9-]+\.)+[a-z]{2,}/[^\s"'<>\\]*"#)
        return rx.matches(in: t, range: NSRange(t.startIndex..., in: t)).compactMap { m -> String? in
            let s = String(t[Range(m.range, in: t)!])
            return hasTracking(s) ? s : nil
        }
    }

    static func hasTracking(_ link: String) -> Bool {
        var rest = Substring(link)
        if let r = rest.range(of: "://") { rest = rest[r.upperBound...] }
        let hash = rest.split(separator: "#", maxSplits: 1, omittingEmptySubsequences: false)
        let fragment = hash.count > 1 ? hash[1] : nil
        let q = hash[0].split(separator: "?", maxSplits: 1, omittingEmptySubsequences: false)
        var groups = [q.count > 1 ? q[1] : ""]
        if let f = fragment, f.contains("=") { groups.append(f.split(separator: "?", omittingEmptySubsequences: false).last ?? "") }
        groups += q[0].split(separator: "/", omittingEmptySubsequences: false).dropFirst().filter { $0.contains("=") }   // after the host
        return groups.contains { params in
            params.split(separator: "&").contains { part in
                let kv = part.split(separator: "=", maxSplits: 1, omittingEmptySubsequences: false)
                let k = String(kv[0]).replacingOccurrences(of: "+", with: " ").removingPercentEncoding ?? String(kv[0])
                let v = kv.count > 1 ? (String(kv[1]).replacingOccurrences(of: "+", with: " ").removingPercentEncoding ?? String(kv[1])) : ""
                return isTracking(k, v)
            }
        }
    }
}
