import { z } from 'zod';

// Enums
export const AppTypeSchema = z.enum(["pos", "dashboard", "invoice", "other"]);
export type AppType = z.infer<typeof AppTypeSchema>;

export const RegionTypeSchema = z.enum([
  "header",
  "input",
  "output",
  "data_table",
  "chart_placeholder",
  "kpi_card"
]);
export type RegionType = z.infer<typeof RegionTypeSchema>;

export const BorderStyleSchema = z.enum([
  "none",
  "thin",
  "medium",
  "thick",
  "double",
  "dashed",
  "dotted"
]);
export type BorderStyle = z.infer<typeof BorderStyleSchema>;

export const HAlignSchema = z.enum(["left", "center", "right", "justify"]);
export type HAlign = z.infer<typeof HAlignSchema>;

export const VAlignSchema = z.enum(["top", "middle", "bottom"]);
export type VAlign = z.infer<typeof VAlignSchema>;

// Style
export const CellStyleSchema = z.object({
  bg_color: z.string().optional(),
  fg_color: z.string().optional(),
  font_size: z.number().default(10),
  bold: z.boolean().default(false),
  italic: z.boolean().default(false),
  border_top: BorderStyleSchema.default("none"),
  border_bottom: BorderStyleSchema.default("none"),
  border_left: BorderStyleSchema.default("none"),
  border_right: BorderStyleSchema.default("none"),
  number_format: z.string().optional(),
  h_align: HAlignSchema.default("left"),
  v_align: VAlignSchema.default("middle")
});
export type CellStyle = z.infer<typeof CellStyleSchema>;

// Validation
export const ValidationSchema = z.object({
  type: z.string(),
  formula1: z.string(),
  allow_blank: z.boolean().default(true),
  error_message: z.string().optional()
});
export type Validation = z.infer<typeof ValidationSchema>;

// Event
export const EventSchema = z.object({
  type: z.string().default("button"),
  action: z.string()
});
export type Event = z.infer<typeof EventSchema>;

// Cell
export const CellSchema = z.object({
  cell_id: z.string(),
  value: z.any().optional(),
  formula: z.string().optional(),
  style: CellStyleSchema.optional(),
  validation: ValidationSchema.optional(),
  event: EventSchema.optional()
});
export type Cell = z.infer<typeof CellSchema>;

// MergeConfig
export const MergeConfigSchema = z.object({
  range: z.string()
});
export type MergeConfig = z.infer<typeof MergeConfigSchema>;

// NamedRange
export const NamedRangeSchema = z.object({
  name: z.string(),
  range: z.string()
});
export type NamedRange = z.infer<typeof NamedRangeSchema>;

// Region
export const RegionSchema = z.object({
  region_id: z.string(),
  type: RegionTypeSchema,
  anchor: z.string(),
  size: z.tuple([z.number(), z.number()]),
  title: z.string().optional().nullable(),
  cell_ids: z.array(z.string())
});
export type Region = z.infer<typeof RegionSchema>;

// Meta
export const MetaSchema = z.object({
  app_type: AppTypeSchema,
  title: z.string(),
  description: z.string(),
  author: z.string().default("SAB Engine"),
  version: z.string().default("1.0.0"),
  frozen_rows: z.number().default(0),
  frozen_cols: z.number().default(0),
  hide_gridlines: z.boolean().default(false),
  col_widths: z.record(z.string(), z.number()).default({}),
  row_heights: z.record(z.string(), z.number()).default({})
});
export type Meta = z.infer<typeof MetaSchema>;

// Blueprint Root
export const BlueprintSchema = z.object({
  meta: MetaSchema,
  regions: z.array(RegionSchema),
  cells: z.array(CellSchema),
  merges: z.array(MergeConfigSchema).default([]),
  named_ranges: z.array(NamedRangeSchema).default([])
});
export type Blueprint = z.infer<typeof BlueprintSchema>;

// Parser function
export function parseBlueprintJson(raw: string): Blueprint {
  const parsed = JSON.parse(raw);
  return BlueprintSchema.parse(parsed);
}
