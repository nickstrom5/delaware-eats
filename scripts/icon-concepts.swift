// Delaware Eats icon concepts, Eats Ranked style v1 (../state-prompts/ICON-STYLE.md): one flat, level, centred food on a plain
// background. Usage: swift scripts/icon-concepts.swift <outdir> -> de-A-peachpie.png, de-B-fries.png, de-C-crab.png (1024)
// All three sit on colonial blue #1F3B6F, the proposed state blue (29 Del. C. § 306 names "arno blue" with no hex). CoreGraphics y is up.
import AppKit
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

func rgb(_ hex: UInt32) -> CGColor {
    CGColor(srgbRed: CGFloat((hex >> 16) & 255) / 255, green: CGFloat((hex >> 8) & 255) / 255, blue: CGFloat(hex & 255) / 255, alpha: 1)
}
let BLUE: UInt32 = 0x1F3B6F

func roundRect(_ r: CGRect, _ rad: CGFloat) -> CGPath { CGPath(roundedRect: r, cornerWidth: rad, cornerHeight: rad, transform: nil) }

/// A: a slice of lattice-top peach pie (Delaware's state dessert), side elevation with the point at the left and the fluted outer
/// crust at the right: the cut side shows the bottom crust, the peach filling and the top crust; the top plane recedes to the rim
/// and shows the lattice over the filling. Crust in the state's buff; 5 colours.
func peachpie(_ c: CGContext, _ s: CGFloat) {
    let CRUST: UInt32 = 0xE3C79A, CRUST_TOP: UInt32 = 0xF2E2C2, PEACH: UInt32 = 0xF3A64B, SEAM: UInt32 = 0xC9A46E
    let x0 = 0.145 * s, x1 = 0.855 * s, rimW = 0.12 * s
    let yb = 0.285 * s, yf = 0.495 * s                      // front (cut) face: bottom and top
    let apexY = 0.705 * s                                     // the far corner of the top plane, above the rim
    // top plane: a triangle from the point (left) to the rim's near and far corners, filled with peach under a lattice
    let top = CGMutablePath()
    top.move(to: CGPoint(x: x0, y: yf)); top.addLine(to: CGPoint(x: x1 - rimW, y: yf)); top.addLine(to: CGPoint(x: x1 - rimW, y: apexY)); top.closeSubpath()
    c.setFillColor(rgb(PEACH)); c.addPath(top); c.fillPath()
    c.saveGState(); c.addPath(top); c.clip()
    c.setStrokeColor(rgb(CRUST_TOP)); c.setLineWidth(40); c.setLineCap(.round)
    for k in 0..<3 {                                          // lattice strips, two directions, round caps
        let x = x0 + CGFloat(0.24 + 0.17 * Double(k)) * s
        c.move(to: CGPoint(x: x - 0.10 * s, y: yf - 0.02 * s)); c.addLine(to: CGPoint(x: x + 0.10 * s, y: apexY + 0.02 * s))
    }
    c.move(to: CGPoint(x: x0, y: yf + 0.055 * s)); c.addLine(to: CGPoint(x: x1, y: yf + 0.055 * s))
    c.strokePath()
    c.restoreGState()
    // cut face: bottom crust, filling, top crust
    c.setFillColor(rgb(SEAM)); c.fill(CGRect(x: x0, y: yb, width: x1 - rimW - x0 + 1, height: 0.045 * s))
    c.setFillColor(rgb(PEACH)); c.fill(CGRect(x: x0, y: yb + 0.045 * s, width: x1 - rimW - x0 + 1, height: 0.125 * s))
    c.setFillColor(rgb(CRUST)); c.fill(CGRect(x: x0, y: yb + 0.17 * s, width: x1 - rimW - x0 + 1, height: yf - yb - 0.17 * s))
    // the fluted outer crust: a tall rounded block at the right end, lighter on top
    let rim = roundRect(CGRect(x: x1 - rimW, y: yb, width: rimW, height: apexY + 0.03 * s - yb), 0.05 * s)
    c.setFillColor(rgb(CRUST)); c.addPath(rim); c.fillPath()
    c.saveGState(); c.addPath(rim); c.clip()
    c.setFillColor(rgb(SEAM)); c.fill(CGRect(x: 0, y: 0, width: s, height: yb + 0.04 * s))
    c.restoreGState()
}

/// B: boardwalk fries in a paper cup (no brand): an upright cup, wider at the top, with one peach-blossom band, and the fries
/// standing up out of it at different heights in two golden tones. 6 colours.
func fries(_ c: CGContext, _ s: CGFloat) {
    let CUP: UInt32 = 0xFBF6EC, BAND: UInt32 = 0xF4A7A3, FRY: UInt32 = 0xF2C14E, FRY2: UInt32 = 0xF7D77F, RIM: UInt32 = 0xE3C79A
    let cx = 0.5 * s, cupTop = 0.505 * s, cupBot = 0.145 * s, topW = 0.40 * s, botW = 0.30 * s
    // fries: capsules from inside the cup up to their own heights (left to right), alternating tones
    let fryW: CGFloat = 0.078 * s
    let tops: [CGFloat] = [0.70, 0.80, 0.86, 0.79, 0.84, 0.73]
    for (i, t) in tops.enumerated() {
        let x = cx - 0.215 * s + CGFloat(i) * 0.0855 * s
        let r = CGRect(x: x - fryW / 2, y: cupTop - 0.10 * s, width: fryW, height: t * s - (cupTop - 0.10 * s))
        // a background-colour gap between neighbours (R7) so each fry reads on its own
        c.setStrokeColor(rgb(BLUE)); c.setLineWidth(20); c.setLineJoin(.round); c.addPath(roundRect(r, fryW / 2)); c.strokePath()
        c.setFillColor(rgb(i % 2 == 0 ? FRY : FRY2)); c.addPath(roundRect(r, fryW / 2)); c.fillPath()
    }
    // the cup
    let cup = CGMutablePath()
    cup.move(to: CGPoint(x: cx - botW / 2, y: cupBot)); cup.addLine(to: CGPoint(x: cx + botW / 2, y: cupBot))
    cup.addLine(to: CGPoint(x: cx + topW / 2, y: cupTop)); cup.addLine(to: CGPoint(x: cx - topW / 2, y: cupTop)); cup.closeSubpath()
    c.setFillColor(rgb(CUP)); c.addPath(cup); c.fillPath()
    c.saveGState(); c.addPath(cup); c.clip()
    c.setFillColor(rgb(BAND)); c.fill(CGRect(x: 0, y: 0.265 * s, width: s, height: 0.105 * s))
    c.setFillColor(rgb(RIM)); c.fill(CGRect(x: 0, y: cupTop - 0.035 * s, width: s, height: 0.035 * s))   // the rolled rim, a shade down
    c.restoreGState()
}

/// C: a steamed blue crab seen from above (its silhouette is the thing everyone knows): the wide carapace with its side points, two
/// big claws forward, three walking legs and a paddle on each side, eyes as two dark dots. Steamed orange-red, a lighter top plane on
/// the shell, darker legs. 5 colours.
func crab(_ c: CGContext, _ s: CGFloat) {
    let SHELL: UInt32 = 0xF26B3A, SHELL_TOP: UInt32 = 0xF7915F, LEG: UInt32 = 0xD94F2B, DARK: UInt32 = 0x3A1A12
    let cx = 0.5 * s, cy = 0.47 * s
    c.setLineCap(.round); c.setLineJoin(.round)
    // walking legs and paddles (behind the shell), symmetric
    c.setStrokeColor(rgb(LEG)); c.setLineWidth(40)
    for side in [-1.0, 1.0] as [CGFloat] {
        for (k, dy) in [0.035, -0.035, -0.10].enumerated() {
            let y0 = cy + CGFloat(dy) * s
            c.move(to: CGPoint(x: cx + side * 0.18 * s, y: y0))
            c.addLine(to: CGPoint(x: cx + side * (0.30 + 0.01 * CGFloat(k)) * s, y: y0 - 0.02 * s))
            c.addLine(to: CGPoint(x: cx + side * (0.345 - 0.01 * CGFloat(k)) * s, y: y0 - 0.085 * s))
        }
        c.move(to: CGPoint(x: cx + side * 0.13 * s, y: cy - 0.11 * s))           // back swimming leg
        c.addLine(to: CGPoint(x: cx + side * 0.21 * s, y: cy - 0.20 * s))
        c.strokePath()
        c.setFillColor(rgb(LEG))                                                   // its paddle
        c.fillEllipse(in: CGRect(x: cx + side * 0.215 * s - 0.045 * s, y: cy - 0.235 * s, width: 0.09 * s, height: 0.07 * s))
    }
    c.strokePath()
    // claws: an arm from the shell, then a big rounded claw with a V notch cut to the background between its two fingers
    for side in [-1.0, 1.0] as [CGFloat] {
        c.setStrokeColor(rgb(SHELL)); c.setLineWidth(52)
        c.move(to: CGPoint(x: cx + side * 0.13 * s, y: cy + 0.07 * s)); c.addLine(to: CGPoint(x: cx + side * 0.21 * s, y: cy + 0.155 * s))
        c.strokePath()
        let px = cx + side * 0.235 * s, py = cy + 0.235 * s
        c.setFillColor(rgb(SHELL)); c.fillEllipse(in: CGRect(x: px - 0.085 * s, y: py - 0.105 * s, width: 0.17 * s, height: 0.21 * s))
        let notch = CGMutablePath()                                                   // the gap between the fingers
        notch.move(to: CGPoint(x: px - side * 0.005 * s, y: py + 0.0 * s))
        notch.addLine(to: CGPoint(x: px - side * 0.10 * s, y: py + 0.075 * s))
        notch.addLine(to: CGPoint(x: px - side * 0.04 * s, y: py + 0.13 * s))
        notch.closeSubpath()
        c.setFillColor(rgb(BLUE)); c.addPath(notch); c.fillPath()
        c.setFillColor(rgb(DARK))                                                    // the dark finger tips of a blue crab's claw
        c.fillEllipse(in: CGRect(x: px - side * 0.07 * s - 21, y: py + 0.025 * s - 21, width: 42, height: 42))
        c.fillEllipse(in: CGRect(x: px + side * 0.0 * s - 21, y: py + 0.088 * s - 21, width: 42, height: 42))
    }
    // the carapace: a wide shell with a point on each side
    let shell = CGMutablePath()
    shell.move(to: CGPoint(x: cx - 0.36 * s, y: cy + 0.035 * s))
    shell.addCurve(to: CGPoint(x: cx, y: cy + 0.12 * s), control1: CGPoint(x: cx - 0.24 * s, y: cy + 0.10 * s), control2: CGPoint(x: cx - 0.12 * s, y: cy + 0.12 * s))
    shell.addCurve(to: CGPoint(x: cx + 0.36 * s, y: cy + 0.035 * s), control1: CGPoint(x: cx + 0.12 * s, y: cy + 0.12 * s), control2: CGPoint(x: cx + 0.24 * s, y: cy + 0.10 * s))
    shell.addCurve(to: CGPoint(x: cx, y: cy - 0.135 * s), control1: CGPoint(x: cx + 0.22 * s, y: cy - 0.03 * s), control2: CGPoint(x: cx + 0.15 * s, y: cy - 0.135 * s))
    shell.addCurve(to: CGPoint(x: cx - 0.36 * s, y: cy + 0.035 * s), control1: CGPoint(x: cx - 0.15 * s, y: cy - 0.135 * s), control2: CGPoint(x: cx - 0.22 * s, y: cy - 0.03 * s))
    shell.closeSubpath()
    c.setFillColor(rgb(SHELL)); c.addPath(shell); c.fillPath()
    c.saveGState(); c.addPath(shell); c.clip()
    c.setFillColor(rgb(SHELL_TOP)); c.fillEllipse(in: CGRect(x: cx - 0.17 * s, y: cy - 0.02 * s, width: 0.34 * s, height: 0.12 * s))   // lighter top plane
    c.restoreGState()
    c.setFillColor(rgb(DARK))                                                     // eyes
    c.fillEllipse(in: CGRect(x: cx - 0.06 * s - 21, y: cy + 0.125 * s - 21, width: 42, height: 42))
    c.fillEllipse(in: CGRect(x: cx + 0.06 * s - 21, y: cy + 0.125 * s - 21, width: 42, height: 42))
}

let out = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "."
func render(_ name: String, _ bg: UInt32, _ f: (CGContext, CGFloat) -> Void) {
    let ctx = CGContext(data: nil, width: 1024, height: 1024, bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpace(name: CGColorSpace.sRGB)!,
                        bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
    ctx.setShouldAntialias(true); ctx.setFillColor(rgb(bg)); ctx.fill(CGRect(x: 0, y: 0, width: 1024, height: 1024))
    f(ctx, 1024)
    let d = CGImageDestinationCreateWithURL(URL(fileURLWithPath: out + "/" + name) as CFURL, UTType.png.identifier as CFString, 1, nil)!
    CGImageDestinationAddImage(d, ctx.makeImage()!, nil); CGImageDestinationFinalize(d)
}
render("de-A-peachpie.png", BLUE, peachpie); render("de-B-fries.png", BLUE, fries); render("de-C-crab.png", BLUE, crab)
print("ok")
