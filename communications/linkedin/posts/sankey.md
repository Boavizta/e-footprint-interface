# Sankey diagrams — LinkedIn post

> Draft for Vincent's personal LinkedIn, to accompany the Sankey video.

𝗲-𝗳𝗼𝗼𝘁𝗽𝗿𝗶𝗻𝘁 𝗳𝗲𝗮𝘁𝘂𝗿𝗲 𝗵𝗶𝗴𝗵𝗹𝗶𝗴𝗵𝘁: new Sankey diagrams tracing impact from usage journeys to hardware

As some of you may know, I’ve spent four years developing e-footprint, an open-source tool within the Boavizta association for modeling the carbon footprint of digital services. It connects how people use a service to the devices and infrastructure behind it.

One of the specificities of e-footprint is that it offers a functional view on top of the technical one: requests to servers are grouped within usage journey steps and journeys, which allows for a clearer understanding of what the system is used for and more useful simulations (such as simulating a new feature that affects a specific usage journey step).

Environmental impact, however, is computed on physical objects: servers, storage, network, user devices. How can we then attribute that impact to the corresponding functionalities? The problem is particularly difficult for servers: when requests from different journey steps and usage patterns reach the same server, what share of the server footprint to attribute to each step and usage journey?

There’s no easy answer: one has to compute the share of CPU and RAM load that is due to each step and journey, even down to the usage pattern.

That attribution logic has been one of e-footprint’s hardest parts to build. And among the tools I know, e-footprint is unique in modeling functionalities and attributing footprint down to them.

The new Sankey diagrams show the result: impact flowing from the whole system through life cycle phases, usage journeys and steps to hardware. Wider flows mean larger shares, so hotspots stand out.

🎥 The video explores an e-commerce model: equal shopper volumes in France and the US lead to equal manufacturing impact, but very different use-phase impact because of electricity carbon intensity. Watch it, then try the diagrams in the e-footprint interface: https://e-footprint.boavizta.org.

#efootprint #boavizta #greenit
