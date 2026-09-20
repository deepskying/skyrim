import type { FoodIconKind } from './food';
// Shared view box and stroke weight keep silhouettes consistent across the grid.
const shapes: Record<FoodIconKind, { body: string; detail?: string }> = {
  soup: { body: 'M12 48h56c-2 21-11 30-28 30S14 69 12 48Z', detail: 'M27 84h26M26 37c-5-6 5-8 0-14m14 14c-5-6 5-8 0-14m14 14c-5-6 5-8 0-14' },
  drink: { body: 'M19 32h42l-5 48H24Z', detail: 'M24 48h32M42 46l6-28h12' },
  wine: { body: 'M33 18h14v22c0 7 12 10 12 20v23H21V60c0-10 12-13 12-20Z', detail: 'M32 25h16M22 59h36M22 74h36' },
  vegetable: { body: 'M24 43c9-11 22-10 28-1 7 11-12 29-34 41-2-14-1-30 6-40Z', detail: 'M43 34c-5-10-2-17 4-20 5 7 5 14 1 21m0 0c6-12 14-13 19-9-2 8-10 11-19 9M26 48l8 5m-13 7 8 5' },
  fruit: { body: 'M40 37c-16-13-29-2-27 15 2 17 13 33 27 25 14 8 25-8 27-25 2-17-11-28-27-15Z', detail: 'M40 37c-2-9 0-15 5-19m0 9c1-10 10-13 17-9-3 9-10 12-17 9' },
  candy: { body: 'M25 40c8-8 22-8 30 0v22c-8 8-22 8-30 0ZM25 42 10 34v34l15-8m30-18 15-8v34l-15-8', detail: 'M34 37v28m12-28v28' },
  meat: { body: 'M27 53c-8-13-2-29 13-31 16-2 27 11 22 25-4 11-14 17-25 15Z', detail: 'm28 57-9 10c-8-2-12 6-7 10 0 7 9 8 12 1l9-12M43 31c7-1 12 5 10 11' },
  bread: { body: 'M13 57c0-17 11-28 27-28s27 11 27 28v19H13Z', detail: 'm26 40-5 12m21-15-6 15m21-10-6 12M14 65h52' },
  cheese: { body: 'M13 51 46 28l21 23v29H13Z', detail: 'M13 51h54M46 28v12M25 63a3 3 0 1 0 0 .1M48 68a4 4 0 1 0 0 .1M58 58h1' },
  fish: { body: 'M13 52c13-22 33-22 46-5l12-12v34L59 57C46 74 26 74 13 52Z', detail: 'M32 36c8 8 8 24 0 32M24 49h1M40 34l6-10 9 14' },
  pastry: { body: 'M15 46h50l-5 32H20ZM15 46c-5-8 1-15 8-15 1-9 12-12 17-6 7-7 17-3 18 5 10-1 15 10 7 16', detail: 'M30 54l2 17m18-17-2 17M27 37h1m22-2h1' },
  ingredient: { body: 'M28 31 24 20h32l-4 11c2 12 15 22 15 37 0 13-12 16-27 16S13 81 13 68c0-15 13-25 15-37Z', detail: 'M28 31h24M40 48v24m0-15-8-6m8 13 8-6' },
  egg: { body: 'M18 61c0-19 12-39 22-39s22 20 22 39c0 15-9 23-22 23S18 76 18 61Z', detail: 'M27 56c0-7 3-14 6-18' },
  other: { body: 'M12 48h56c-2 21-11 30-28 30S14 69 12 48Z', detail: 'M27 84h26' },
};
export function FoodIcon({ kind }: { kind: FoodIconKind }) {
  const shape = shapes[kind];
  return <svg className="potion-bottle food-icon" viewBox="0 0 80 100" aria-hidden="true" data-food-icon={kind}><path className="food-icon-body" d={shape.body}/>{shape.detail && <path className="food-icon-detail" d={shape.detail}/>}</svg>;
}
