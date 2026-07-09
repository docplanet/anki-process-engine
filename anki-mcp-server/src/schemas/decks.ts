import { z } from "zod";

export const CreateDeckInputSchema = z
  .object({
    deck_name: z.string().min(1).describe("Deck name to create, e.g. 'Neurogenetics::Week 2'"),
  })
  .strict();
export type CreateDeckInput = z.output<typeof CreateDeckInputSchema>;
