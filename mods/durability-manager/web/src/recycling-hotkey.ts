const letters = [0x1e,0x30,0x2e,0x20,0x12,0x21,0x22,0x23,0x17,0x24,0x25,0x26,0x32,0x31,0x18,0x19,0x10,0x13,0x1f,0x14,0x16,0x2f,0x11,0x2d,0x15,0x2c];
const modifiers: Record<string, number> = { ShiftLeft: 0x2a, ShiftRight: 0x36, ControlLeft: 0x1d, ControlRight: 0x9d, AltLeft: 0x38, AltRight: 0xb8 };
export function recyclingKeyCode(code: string): number | undefined {
  if (/^Key[A-Z]$/.test(code)) return letters[code.charCodeAt(3) - 65];
  if (/^F([1-9]|1[0-2])$/.test(code)) { const n = Number(code.slice(1)); return n <= 10 ? 0x3a + n : n === 11 ? 0x57 : 0x58; }
  return modifiers[code] ?? ({ Delete: 0xd3, Space: 0x39 } as Record<string, number>)[code];
}
export function recyclingKeyLabel(code: number): string {
  const mod = Object.entries(modifiers).find(([, value]) => value === code)?.[0];
  if (mod) return `${mod.endsWith('Right') ? '右' : '左'} ${mod.startsWith('Control') ? 'Ctrl' : mod.startsWith('Shift') ? 'Shift' : 'Alt'}`;
  const index = letters.indexOf(code);
  if (index >= 0) return String.fromCharCode(65 + index);
  if (code >= 0x3b && code <= 0x44) return `F${code - 0x3a}`;
  return ({ [0x57]: 'F11', [0x58]: 'F12', [0xd3]: 'Delete', [0x39]: 'Space' } as Record<number, string>)[code] ?? `Scan ${code}`;
}

export function createRecyclingCapture() {
  const held = new Set<string>();
  let rejected = false;
  return (code: string, down: boolean): { keyCode: number; safetyCode: number } | 'invalid' | undefined => {
    if (modifiers[code]) {
      if (down) { held.add(code); if (held.size > 1) rejected = true; return; }
      const wasHeld = held.delete(code);
      if (!wasHeld || held.size) return;
      if (rejected) { rejected = false; return 'invalid'; }
      return { keyCode: modifiers[code], safetyCode: modifiers[code] };
    }
    if (!down) return;
    if (!held.size) rejected = false;
    const keyCode = recyclingKeyCode(code);
    if (!keyCode || rejected || held.size > 1) { rejected = held.size > 0; return 'invalid'; }
    const modifier = Array.from(held)[0];
    return { keyCode, safetyCode: modifier ? modifiers[modifier] : keyCode };
  };
}
