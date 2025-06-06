## Current Status
Easy Artistry is a tool for human artists. It's intention is to utilize AI image generation to enhance and propagate the skills of talented artists. This is in contrast to the current trajectory of image generation technology, which seems to be focused on replicating and potentially replacing the work of human artists. We believe that not only is that direction an unfortunate and unethical way to utilize powerful tools, but also that it will reduce the quality of published artwork in general. While AI tools may eventually surpass humans in terms of clinical or academic technique, the core relatability and positivity of much human-created artwork is dependent on said work being an expression of the artist in some sense. This expression is explicitly individual, and thus will not be replicated by current machine learning techniques.

The goal, therefore, of Easy Artistry, is to reduce both the barrier to entry, time, and resources required to produce art and tell stories visually for human artists. Thus, using the power of these models to amplify individual expression and style, whilst discouraging dull, cooperate, or "soulless" AI artwork.

Currently, Easy Artistry is a fork of Stable Diffusion Webui. We had decided to utilize the existing image generation front-end as a jumping off point. We devised and implemented several features to start moving the software in our intended direction. 

- Invisible watermarks, with the intention to hold users accountable for publishing AI generated work. By marking images as AI generated without degrading the image, the goal is to future-proof the software against being used to directly publish AI images, even if they become indistinguishable (at a glace) from human work. 
- Prompt-based templates. Many image generation models require prompts to include particular words or phrases to produce quality results. Additionally, these models may also change styles or tendencies based on the keywords in the prompt. These templates pre-fill prompts with the appropriate "prompt engineering" to produce predictable results, hopefully allowing beginners or entirely art-focused parties to get desired results without having to learn the quirks of the system. 
- UI changes. We have modified the UI of Stable Diffusion Webui to better suit our needs. This semester, we have no members with a history in front-end, so these skills will have to be relearned when designed the new front end.

## Future Plans
Over the previous semesters, the team spent a large portion of their time playing "catchup" with the current technology. As models and API's improve and changed, it took quite a bit of work to simply avoid becoming obsolete. Combine that with the time it takes to learn the required skills, and parse the codebase given the terrible documentation it was difficult to get much development done. 

Our goal this semester is to begin the process of creating a robust alpha version of the software, that will not only support Stable Diffusion, but any local image generation model or API. This way, if the "industry standard" changes, or if the user wants increased customizability, the transition should be either possible entirely within the software, or with minimal work from the dev team. 

Because of this, we are looking to transition away from Stable Diffusion Webui and Stable Diffusion in general in favor of a custom solution with a similar structure. The primary differences are as follows:
- Thorough documentation for developers, likely in the form of a wiki, to speed up the process of familiarizing oneself with the codebase and troubleshooting.
- Modular design, so that certain aspects of the codebase can be swapped in and out as needs change, and to easily maintain the state-of-the-art. 
- A more robust backend. Currently, the "backend" is primarily the model itself, installed locally. We want to replace this with an interface that will detect available image generation options, either locally installed models or APIs, and automatically run each option in order to seamlessly integrate these systems with the front-end.

## Basic Schedule
- Within the first 2 weeks, we hope to have a bare bones window and UI.
- By the midpoint of the semester, we want image generation to work, as well as some of the existing EA features.
- By the end of the semester, we would like to have a more robust UI, and a good framework for future development. 
- Throughout this process, we will be actively working on the LLM prompt enhancement, and experimenting with model training. These don't have a definitive date, but by the end of the semester, we hope to have enhancement working and at least a few LoRAs trained.