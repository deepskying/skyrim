const glyphs: Record<string, string> = {
  all: '\ue60a', favorite: '\ue610', weapon: '\uead0', armor: '\ue6a6', potion: '\ue6fd', scroll: '\ue601', food: '\ue602', ingredient: '\ue675', misc: '\ue60b',
  magic: '\uec5b', destruction: '\ue63e', alteration: '\ue908', illusion: '\ue642', restoration: '\ue65f', conjuration: '\ue606', shout: '\ue600', power: '\ue7af', status: '\ue642',
  gold: '\ueb19', weight: '\ue7f6', equipped: '\uf0dc', enchanted: '\ue898', quest: '\ue63f', stolen: '\ue7ae', search: '\ue603', close: '\ue609', left: '\ue605', right: '\ue604',
};

export function Icon({ name, className = '' }: { name: string; className?: string }) {
  return <span aria-hidden="true" className={`icon icon-${name} ${className}`}>{glyphs[name] ?? glyphs.misc}</span>;
}
