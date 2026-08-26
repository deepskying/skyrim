const glyphs: Record<string, string> = {
  all: '\ue678', favorite: '\ue839', weapon: '\ueba4', armor: '\ueb53', potion: '\ue8ae', scroll: '\ue640', food: '\ueab6', ingredient: '\ue643', misc: '\ue65f',
  magic: '\ue886', destruction: '\ue866', alteration: '\ue667', illusion: '\ue706', restoration: '\ue922', conjuration: '\ue632', shout: '\ue67f', power: '\ue7b8', status: '\ue633',
  gold: '\ueb19', weight: '\ue612', equipped: '\ue83a', enchanted: '\ue898', quest: '\ue651', stolen: '\ue7ae', search: '\ue753', close: '\ue609', left: '\ue602', right: '\ue743',
};

export function Icon({ name, className = '' }: { name: string; className?: string }) {
  return <span aria-hidden="true" className={`icon icon-${name} ${className}`}>{glyphs[name] ?? glyphs.misc}</span>;
}
