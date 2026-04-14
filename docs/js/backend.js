const PROVIDER_DEFAULTS = {
  openai: {
    endpoint: "https://api.openai.com/v1",
    model: "gpt-4o-mini",
  },
  nvidia: {
    endpoint: "https://integrate.api.nvidia.com/v1",
    model: "nvidia/llama-3.1-nemotron-ultra-253b-v1",
  },
};

export class ProviderClient {
  constructor({ provider, endpoint, apiKey, model, userName }) {
    this.provider = provider;
    this.endpoint = endpoint?.trim() || ProviderClient.defaultEndpoint(provider);
    this.apiKey = apiKey?.trim();
    this.model = model?.trim() || ProviderClient.defaultModel(provider);
    this.userName = userName?.trim() || "";
  }

  static defaultEndpoint(provider) {
    return PROVIDER_DEFAULTS[provider]?.endpoint || "";
  }

  static defaultModel(provider) {
    return PROVIDER_DEFAULTS[provider]?.model || "";
  }

  _buildPayload(query) {
    const systemContent = this.userName
      ? `You are PraSush, a bilingual AI assistant. The user's name is ${this.userName}. Answer clearly in Hindi or English depending on the user's message.`
      : "You are PraSush, a bilingual AI assistant. Answer clearly in Hindi or English depending on the user's message.";

    return {
      model: this.model,
      messages: [
        {
          role: "system",
          content: systemContent,
        },
        {
          role: "user",
          content: query,
        },
      ],
      temperature: 0.5,
      max_tokens: 320,
    };
  }

  _buildVisionPayload(query, imageData) {
    const systemContent = this.userName
      ? `You are PraSush, a bilingual AI assistant with vision. The user's name is ${this.userName}. The user asked a visual question. Use the captured scene image and reply naturally in the same language.`
      : "You are PraSush, a bilingual AI assistant with vision. The user asked a visual question. Use the captured scene image and reply naturally in the same language.";
    const userContent = [
      { type: "text", text: query },
      { type: "image_url", image_url: { url: imageData } },
    ];

    return {
      model: this.model,
      messages: [
        { role: "system", content: systemContent },
        { role: "user", content: userContent },
      ],
      temperature: 0.5,
      max_tokens: 320,
    };
  }

  async chat(query, imageData = null) {
    if (!this.apiKey) {
      throw new Error("API key is required.");
    }
    if (!this.endpoint) {
      throw new Error("Endpoint URL is required.");
    }

    const url = `${this.endpoint.replace(/\/+$/, "")}/chat/completions`;
    const payload = imageData ? this._buildVisionPayload(query, imageData) : this._buildPayload(query);
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const details = await response.text();
      throw new Error(`Request failed ${response.status} ${response.statusText}: ${details}`);
    }

    const data = await response.json();
    return ProviderClient._parseChoice(data);
  }

  static _parseChoice(data) {
    const choices = Array.isArray(data?.choices) ? data.choices : [];
    if (!choices.length) {
      throw new Error("No choices returned from the model.");
    }

    const first = choices[0];
    const message = first?.message || {};
    let content = typeof message.content === "string" ? message.content : first?.content;

    if (!content || !content.trim()) {
      content = typeof message.reasoning_content === "string" ? message.reasoning_content : first?.reasoning_content;
    }

    if (!content || !content.trim()) {
      throw new Error("Model response did not contain assistant content.");
    }

    return content.trim();
  }
}
