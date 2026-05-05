import torch

def check_mac_ai_setup():
    print("Starte System-Check für KI-Modelle...")
    print("-" * 40)
    
    # Prüfen, ob PyTorch generell läuft
    print(f"PyTorch Version: {torch.__version__}")
    
    # Das ist der wichtigste Teil für dich als Mac-User!
    # MPS steht für "Metal Performance Shaders" (Apples Version von Grafikkarten-Beschleunigung)
    if torch.backends.mps.is_available():
        print("✅ ERFOLG: Dein Mac M-Chip (MPS) wurde erkannt!")
        print("   Das LTX 2.3 Video-Modell kann die Hardware-Beschleunigung nutzen.")
        
        # Test-Berechnung auf dem Grafikchip durchführen
        try:
            device = torch.device("mps")
            x = torch.ones(1, device=device)
            print("✅ ERFOLG: Test-Berechnung auf dem Grafikchip war erfolgreich.")
        except Exception as e:
            print(f"❌ FEHLER bei der Test-Berechnung auf dem MPS-Chip: {e}")
            
    elif torch.backends.mps.is_built():
        print("⚠️ WARNUNG: MPS ist in dieser PyTorch-Installation eingebaut, aber nicht verfügbar.")
        print("   Möglicherweise musst du dein macOS aktualisieren (benötigt mindestens macOS 12.3).")
    else:
        print("❌ FEHLER: MPS nicht gefunden.")
        print("   Dein Mac wird KI-Modelle nur über die CPU berechnen. Das wird für Videogenerierung extrem langsam sein.")
        print("   Hast du einen Mac mit Intel-Prozessor?")

if __name__ == "__main__":
    check_mac_ai_setup()