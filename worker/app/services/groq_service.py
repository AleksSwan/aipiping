import json

from groq import AsyncGroq
from groq.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from shared.utils.logger_configurator import LoggerConfigurator

# Configure the logger
logger = LoggerConfigurator(name="groq_service").configure()


class GroqService:
    def __init__(
        self,
        model: str = "llama3-70b-8192",
        temperature: float = 0.01,
        max_tokens: int = 1024,
    ):
        self.client = AsyncGroq()
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _system_message(self) -> ChatCompletionSystemMessageParam:
        """
        Generate the system message for the Groq API request.
        This message provides the instructions for the AI assistant.

        :return: A list containing the system message.
        """
        return {
            "role": "system",
            "content": (
                "You are a helpful tourist consultant. "
                "You must recommend three things to do in a given country during a specific season. "
                "Your answer must be short and concise. "
                "Don't use markdown in your answers. "
                "Return answer in JSON format with recommendation number as dictionary key."
            ),
        }

    async def _chat_completion(
        self,
        system_message: ChatCompletionSystemMessageParam,
        user_message: ChatCompletionUserMessageParam,
    ) -> str | None:
        chat_completion = await self.client.chat.completions.create(
            messages=[system_message, user_message],
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stop=None,
            stream=False,
        )
        return chat_completion.choices[0].message.content

    async def generate_recommendations(self, prompt: str) -> dict:
        """
        Generate travel recommendations using the Groq API based on the given prompt.

        :param prompt: The prompt to send to the Groq API.
        :return: A dictionary containing the recommendations.
        """
        system_message: ChatCompletionSystemMessageParam = self._system_message()
        user_message: ChatCompletionUserMessageParam = {
            "role": "user",
            "content": prompt,
        }

        chat_recommendations = await self._chat_completion(system_message, user_message)

        if chat_recommendations is None:
            recommendations = {"1": "No recommendations available"}
        else:
            try:
                recommendations = json.loads(chat_recommendations)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse recommendations: {chat_recommendations}")
                recommendations = {"1": chat_recommendations}
        logger.info(f"Recommendations for [{prompt}]: {recommendations}")
        return recommendations
