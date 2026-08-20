import Foundation
import AppKit
import Vision
import CoreGraphics

// bookgrab-helper — utilitários nativos macOS: seleção de área, OCR (Vision),
// envio de teclas e cliques. Usado pelo grab.py.

func die(_ msg: String) -> Never {
    FileHandle.standardError.write(Data(("bookgrab: " + msg + "\n").utf8))
    exit(1)
}

func out(_ s: String) {
    FileHandle.standardOutput.write(Data((s + "\n").utf8))
}

// MARK: - Seleção de área

final class SelectionView: NSView {
    var start: NSPoint?
    var current: NSPoint?
    var onDone: ((NSRect) -> Void)?

    override var acceptsFirstResponder: Bool { true }

    private var selection: NSRect? {
        guard let s = start, let c = current else { return nil }
        return NSRect(x: min(s.x, c.x), y: min(s.y, c.y),
                      width: abs(c.x - s.x), height: abs(c.y - s.y))
    }

    override func draw(_ dirtyRect: NSRect) {
        NSColor(calibratedWhite: 0, alpha: 0.35).setFill()
        dirtyRect.fill()

        guard let r = selection else {
            drawHint("Arrasta para delimitar a área da página  ·  Esc para cancelar")
            return
        }
        // "buraco" transparente na zona escolhida
        NSColor.clear.set()
        r.fill(using: .copy)
        NSColor.systemBlue.setStroke()
        let path = NSBezierPath(rect: r)
        path.lineWidth = 2
        path.stroke()
        drawLabel("\(Int(r.width)) × \(Int(r.height))", at: NSPoint(x: r.minX, y: r.maxY + 6))
    }

    private func attrs(_ size: CGFloat) -> [NSAttributedString.Key: Any] {
        [.font: NSFont.monospacedDigitSystemFont(ofSize: size, weight: .medium),
         .foregroundColor: NSColor.white,
         .backgroundColor: NSColor(calibratedWhite: 0, alpha: 0.6)]
    }

    private func drawLabel(_ text: String, at p: NSPoint) {
        NSAttributedString(string: " \(text) ", attributes: attrs(13)).draw(at: p)
    }

    private func drawHint(_ text: String) {
        let s = NSAttributedString(string: "  \(text)  ", attributes: attrs(18))
        let size = s.size()
        s.draw(at: NSPoint(x: bounds.midX - size.width / 2, y: bounds.midY - size.height / 2))
    }

    override func resetCursorRects() {
        addCursorRect(bounds, cursor: .crosshair)
    }

    override func mouseDown(with e: NSEvent) {
        start = convert(e.locationInWindow, from: nil)
        current = start
        needsDisplay = true
    }

    override func mouseDragged(with e: NSEvent) {
        current = convert(e.locationInWindow, from: nil)
        needsDisplay = true
    }

    override func mouseUp(with e: NSEvent) {
        current = convert(e.locationInWindow, from: nil)
        guard let r = selection, r.width >= 8, r.height >= 8 else {
            die("seleção demasiado pequena")
        }
        onDone?(r)
    }

    override func keyDown(with e: NSEvent) {
        if e.keyCode == 53 { exit(2) } // Esc
    }
}

func runSelect() {
    let app = NSApplication.shared
    app.setActivationPolicy(.regular)

    let union = NSScreen.screens.reduce(NSRect.zero) { $0.isEmpty ? $1.frame : $0.union($1.frame) }
    guard !union.isEmpty, let mainScreen = NSScreen.screens.first else { die("sem ecrãs") }

    let win = NSWindow(contentRect: union, styleMask: .borderless, backing: .buffered, defer: false)
    win.isOpaque = false
    win.backgroundColor = .clear
    win.level = .screenSaver
    win.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary]
    win.ignoresMouseEvents = false

    let view = SelectionView(frame: NSRect(origin: .zero, size: union.size))
    view.onDone = { r in
        // coordenadas AppKit (origem em baixo-à-esquerda do ecrã principal)
        let gx = r.minX + union.minX
        let gyBottom = r.minY + union.minY
        // screencapture usa origem no topo-esquerdo do ecrã principal
        let top = mainScreen.frame.maxY - (gyBottom + r.height)
        out("{\"x\":\(Int(gx.rounded())),\"y\":\(Int(top.rounded())),\"w\":\(Int(r.width.rounded())),\"h\":\(Int(r.height.rounded()))}")
        exit(0)
    }
    win.contentView = view
    win.makeKeyAndOrderFront(nil)
    win.makeFirstResponder(view)
    app.activate(ignoringOtherApps: true)
    app.run()
}

// MARK: - OCR

struct Line {
    var text: String
    var minX: Double
    var maxX: Double
    var midY: Double
    var height: Double
    var width: Double { maxX - minX }
}

/// Carrega um ficheiro como uma ou mais imagens. PDFs são rasterizados
/// a ~180 dpi, página a página; tudo o resto vai direto via NSImage.
func carregar(path: String) -> [CGImage] {
    if path.lowercased().hasSuffix(".pdf") {
        guard let doc = CGPDFDocument(URL(fileURLWithPath: path) as CFURL) else {
            die("não consegui abrir o PDF: \(path)")
        }
        var imgs: [CGImage] = []
        let escala: CGFloat = 2.5
        for n in 1...max(doc.numberOfPages, 1) {
            guard let pg = doc.page(at: n) else { continue }
            let caixa = pg.getBoxRect(.mediaBox)
            let w = Int(caixa.width * escala), h = Int(caixa.height * escala)
            guard w > 0, h > 0,
                  let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8,
                                      bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(),
                                      bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)
            else { continue }
            ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
            ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
            ctx.scaleBy(x: escala, y: escala)
            ctx.translateBy(x: -caixa.minX, y: -caixa.minY)
            ctx.drawPDFPage(pg)
            if let img = ctx.makeImage() { imgs.append(img) }
        }
        if imgs.isEmpty { die("PDF sem páginas legíveis: \(path)") }
        return imgs
    }
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        die("não consegui abrir a imagem: \(path)")
    }
    return [cg]
}

func recognize(cg: CGImage, langs: [String], fast: Bool, correcao: Bool, reflow: Bool,
               trimTop: Double, trimBottom: Double, minHeight: Double) -> String {

    let req = VNRecognizeTextRequest()
    req.recognitionLevel = fast ? .fast : .accurate
    req.usesLanguageCorrection = correcao
    req.recognitionLanguages = langs
    req.minimumTextHeight = Float(minHeight)

    do {
        try VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
    } catch {
        die("OCR falhou: \(error.localizedDescription)")
    }

    let obs = (req.results ?? []).filter { o in
        // boundingBox tem origem em baixo-à-esquerda; converter para fração a partir do topo
        let fromTop = 1.0 - Double(o.boundingBox.maxY)
        let fromBottom = Double(o.boundingBox.minY)
        return fromTop >= trimTop && fromBottom >= trimBottom
    }
    guard !obs.isEmpty else { return "" }

    // agrupar observações em linhas de leitura
    let sorted = obs.sorted { $0.boundingBox.midY > $1.boundingBox.midY }
    var groups: [[VNRecognizedTextObservation]] = []
    for o in sorted {
        let h = Double(o.boundingBox.height)
        if var last = groups.last,
           let ref = last.first,
           abs(Double(ref.boundingBox.midY) - Double(o.boundingBox.midY)) < h * 0.6 {
            last.append(o)
            groups[groups.count - 1] = last
        } else {
            groups.append([o])
        }
    }

    var lines: [Line] = []
    for g in groups {
        let ordered = g.sorted { $0.boundingBox.minX < $1.boundingBox.minX }
        let text = ordered.compactMap { $0.topCandidates(1).first?.string }
            .joined(separator: " ")
            .trimmingCharacters(in: .whitespaces)
        if text.isEmpty { continue }
        let minX = ordered.map { Double($0.boundingBox.minX) }.min() ?? 0
        let maxX = ordered.map { Double($0.boundingBox.maxX) }.max() ?? 0
        let midY = ordered.map { Double($0.boundingBox.midY) }.reduce(0, +) / Double(ordered.count)
        let hh = ordered.map { Double($0.boundingBox.height) }.max() ?? 0
        lines.append(Line(text: text, minX: minX, maxX: maxX, midY: midY, height: hh))
    }
    guard !lines.isEmpty else { return "" }
    if !reflow { return lines.map(\.text).joined(separator: "\n") }

    // reflow: juntar linhas do mesmo parágrafo, desfazer hifenização
    let bodyWidth = lines.map(\.width).max() ?? 1
    let leftEdge = lines.map(\.minX).min() ?? 0
    var paragraphs: [String] = []
    var buf = ""
    for (i, line) in lines.enumerated() {
        if buf.isEmpty {
            buf = line.text
        } else if buf.hasSuffix("-") || buf.hasSuffix("\u{2010}") {
            buf = String(buf.dropLast()) + line.text
        } else {
            buf += " " + line.text
        }

        let isLast = i == lines.count - 1
        let short = line.width < bodyWidth * 0.85
        let endsSentence = line.text.range(of: "[.!?:;\"»”]$", options: .regularExpression) != nil
        let nextIndented = !isLast && lines[i + 1].minX > leftEdge + 0.02
        let bigGap = !isLast && (line.midY - lines[i + 1].midY) > line.height * 2.0

        if isLast || (short && endsSentence) || nextIndented || bigGap {
            paragraphs.append(buf)
            buf = ""
        }
    }
    if !buf.isEmpty { paragraphs.append(buf) }
    return paragraphs.joined(separator: "\n\n")
}

func runOCR(_ args: [String]) {
    var path: String?
    var langs = ["pt-BR", "en-US"]
    var fast = false, reflow = false, correcao = true
    var trimTop = 0.0, trimBottom = 0.0, minHeight = 0.008
    var i = 0
    while i < args.count {
        let a = args[i]
        switch a {
        case "--langs": i += 1; langs = args[i].split(separator: ",").map(String.init)
        case "--fast": fast = true
        case "--sem-correcao": correcao = false
        case "--reflow": reflow = true
        case "--trim-top": i += 1; trimTop = Double(args[i]) ?? 0
        case "--trim-bottom": i += 1; trimBottom = Double(args[i]) ?? 0
        case "--min-height": i += 1; minHeight = Double(args[i]) ?? 0.008
        default: path = a
        }
        i += 1
    }
    guard let p = path else { die("falta o caminho da imagem") }
    let paginas = carregar(path: p).map {
        recognize(cg: $0, langs: langs, fast: fast, correcao: correcao, reflow: reflow,
                  trimTop: trimTop, trimBottom: trimBottom, minHeight: minHeight)
    }
    out(paginas.joined(separator: "\n\n"))
}

// MARK: - Teclas e cliques

func runKey(_ args: [String]) {
    guard let code = args.first.flatMap({ UInt16($0) }) else { die("uso: key <keycode>") }
    let src = CGEventSource(stateID: .hidSystemState)
    CGEvent(keyboardEventSource: src, virtualKey: code, keyDown: true)?.post(tap: .cghidEventTap)
    usleep(30_000)
    CGEvent(keyboardEventSource: src, virtualKey: code, keyDown: false)?.post(tap: .cghidEventTap)
}

func runClick(_ args: [String]) {
    guard args.count >= 2, let x = Double(args[0]), let y = Double(args[1]) else {
        die("uso: click <x> <y>")
    }
    let p = CGPoint(x: x, y: y)
    let src = CGEventSource(stateID: .hidSystemState)
    CGEvent(mouseEventSource: src, mouseType: .mouseMoved, mouseCursorPosition: p, mouseButton: .left)?.post(tap: .cghidEventTap)
    usleep(20_000)
    CGEvent(mouseEventSource: src, mouseType: .leftMouseDown, mouseCursorPosition: p, mouseButton: .left)?.post(tap: .cghidEventTap)
    usleep(30_000)
    CGEvent(mouseEventSource: src, mouseType: .leftMouseUp, mouseCursorPosition: p, mouseButton: .left)?.post(tap: .cghidEventTap)
}

func runLangs() {
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    if let l = try? req.supportedRecognitionLanguages() {
        out(l.joined(separator: "\n"))
    }
}

// MARK: - dispatch

let argv = Array(CommandLine.arguments.dropFirst())
switch argv.first {
case "select": runSelect()
case "ocr": runOCR(Array(argv.dropFirst()))
case "key": runKey(Array(argv.dropFirst()))
case "click": runClick(Array(argv.dropFirst()))
case "langs": runLangs()
default:
    die("uso: bookgrab-helper select|ocr|key|click|langs")
}
