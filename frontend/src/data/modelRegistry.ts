// List of available providers
export const providers = ["OpenRouter", "HuggingFace"];
export interface ModelRegistryEntry {
  primary_model: string;
  candidate_models?: string[];
}

export const MODEL_REGISTRY: Record<string, ModelRegistryEntry> = {
  openrouter: {
    primary_model: "openai/gpt-oss-20b:free",
    candidate_models: [
      "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
      "nvidia/nemotron-nano-9b-v2:free",
    ],
  },
  huggingface: {
    primary_model: "deepseek-ai/DeepSeek-R1",
    candidate_models: [],
  },
};

export const getModelsForProvider = (provider: string) => {
  const config = MODEL_REGISTRY[provider.toLowerCase()];
  if (!config) return ["Automatic Model Selection (Model Routing)"];
  return [
    "Automatic Model Selection (Model Routing)",
    config.primary_model,
    ...(config.candidate_models || []),
  ];
};