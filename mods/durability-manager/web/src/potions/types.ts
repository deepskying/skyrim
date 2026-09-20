export type PotionEffect = { id: number; name: string; traits: string[]; description: string; magnitude: number; duration: number; area: number; hasMagnitude: boolean; hasDuration: boolean; harmful: boolean; conditional?: boolean };
export type Potion = { poison?: boolean; keywords?: string[]; localId?: number; id: number; name: string; count: number; weight: number; value: number; source: string; effects: PotionEffect[]; usable: boolean; reason: string };
export type PotionState = { items: Potion[]; token: number; message: string; reply?: { requestID: number; ok: boolean } };
