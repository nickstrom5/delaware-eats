import Foundation

/// Delaware Eats' side of the data updates (OTA-DATA.md): one places.json (the places plus each place's detail record), checked with
/// the loader launch uses. A detail record for an id the file has no place for is never shown, so it doesn't fail the check (the shared
/// tests' cut-down copies keep the whole "detail" object).
extension DataLayout {
    static let app = DataLayout(kind: .single, bundled: Bundle.main.resourceURL!, head: "places") { folder in
        let (file, places, _) = try AppModel.readAll(folder.appending(path: "places.json"))
        return DataSummary(generated: file.generated, rows: ["places": places.count], places: places.count)
    }
}
