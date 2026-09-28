# Detector limitations: what to cite and how

Use one to three of these in a response or packet. More than that reads as an argument with the reviewer instead of an answer to the allegation. Choose the source closest to the reviewer's situation: the vendor's own guidance for a Turnitin case, the non-native writer study for an English-as-an-additional-language writer, and so on.

Sources checked September 2026. Detector vendors revise their guidance, so re-check anything time-sensitive with a web search before quoting it, and quote it as dated ("as of [month year], Turnitin's guidance says...").

## How to cite without overclaiming

- Quote or paraphrase exactly what the source says. Do not round "more than half" up to "most", or turn "may misidentify" into "is usually wrong".
- The point to make is narrow: **a detector score alone is not evidence of misconduct**, and the writer's process evidence answers the question the score cannot. Do not claim that detectors never work, or that a score proves nothing about anyone.
- Be careful with studies that cut both ways. The Weber-Wulff study found the tools unreliable overall, but also found them more likely to miss AI text than to flag human text. Cite it for unreliability, not for a false-positive rate.

## Vendor guidance

**Turnitin: not a sole basis for adverse action.**
Turnitin's own documentation says its AI writing detection "may not always be accurate (it may misidentify human-written, AI-generated, and AI-paraphrased text), so it should not be used as the sole basis for adverse actions against a student", and that determining misconduct takes "further scrutiny and human judgment in conjunction with an organization's application of its specific academic policies". Turnitin also marks scores below 20% with an asterisk because false positives are more frequent in that range.
Source: Turnitin Guides, "AI writing detection model": https://guides.turnitin.com/hc/en-us/articles/28294949544717-AI-writing-detection-model

**GPTZero: not for punishment.**
GPTZero's FAQ says its results "should not be used to punish students", recommends using them "as part of a holistic assessment of student work", and acknowledges edge cases "where AI is classified as human, and human is classified as AI". It suggests educators look at writing-process evidence such as revision history and ask students to demonstrate their understanding, and says "a long-term pattern of AI use, as opposed to a single instance" should inform conclusions.
Source: GPTZero FAQ: https://gptzero.me/faq

**OpenAI withdrew its own AI text classifier.**
OpenAI released an AI-text classifier in January 2023 and withdrew it on 20 July 2023 "due to its low rate of accuracy". At launch, OpenAI reported that it identified 26% of AI-written text correctly and labelled human-written text as AI-written 9% of the time.
Source: OpenAI, "New AI classifier for indicating AI-written text" (with July 2023 update): https://openai.com/index/new-ai-classifier-for-indicating-ai-written-text/

## Research

**Non-native English writers are flagged far more often.**
Liang et al. tested seven detectors. More than half of the TOEFL essays written by non-native English speakers were misclassified as AI-generated, while essays by US eighth-graders were classified almost perfectly. Making the non-native writing's vocabulary richer reduced misclassification; simplifying native writing increased it. This is the most relevant source for writers whose English is plain, formal or learned later in life.
Source: Liang, Yuksekgonul, Mao, Wu & Zou (2023), "GPT detectors are biased against non-native English writers", *Patterns* 4(7): https://www.cell.com/patterns/fulltext/S2666-3899(23)00130-7 (preprint: https://arxiv.org/abs/2304.02819)

**Detection tools were found neither accurate nor reliable.**
Weber-Wulff et al. tested 14 detection tools and concluded that they are "neither accurate nor reliable". Their errors leaned toward classifying text as human-written, and machine translation and light obfuscation reduced accuracy further.
Source: Weber-Wulff et al. (2023), "Testing of detection tools for AI-generated text", *International Journal for Educational Integrity* 19, 26: https://link.springer.com/article/10.1007/s40979-023-00146-z

## Institutional decisions

**Vanderbilt disabled Turnitin's AI detector.**
In August 2023 Vanderbilt University turned off Turnitin's AI detection, citing a lack of transparency about how it works, the risk of false accusations at the scale of tens of thousands of papers a year, and evidence of bias against non-native English writers.
Source: Vanderbilt University, "Guidance on AI Detection and Why We're Disabling Turnitin's AI Detector" (16 August 2023): https://www.vanderbilt.edu/brightspace/2023/08/16/guidance-on-ai-detection-and-why-were-disabling-turnitins-ai-detector/

If the writer's own institution has published guidance on AI detection, cite that first. A reviewer is bound by their own institution's policy, so it outweighs anything above. Search for "[institution] AI detection guidance" or "[institution] academic integrity generative AI".

## Things not to cite

- Viral anecdotes (famous texts scored as AI) unless you can link a reputable original source. They are easy to dismiss.
- Marketing pages from detector competitors or "humanizer" companies. They have an interest in the conclusion.
- Accuracy percentages without a source and date.
- Claims about a detector's internals that the vendor has not published.
