# AI bootstrap for edge systems

The description panel of Start with AI gets a scope choice: **Web only**, as today, or **Web + edge**
for a system that also runs on devices deployed in the field.

## Problem

Start with AI builds a first modeling from a description, but only a web one. Its guidance, its
instructions to the AI and its review checklist speak of usage journeys, servers and APIs only. A
user describing a sensor fleet, a building gateway or an industrial PC gets a modeling with no edge
objects: the devices are left out, or misread as the user's own devices. Industrial users, who
model edge fleets and mixed web and edge systems, have to build the edge part by hand from an empty
canvas.

## The change

Above the description, the user chooses **Web only** (the default) or **Web + edge**. Web + edge
covers the deployed devices, what they run, how many are deployed and for how long, the servers they
call, and the usage journeys of people around them, such as a dashboard. There is no edge-only
choice: an edge system almost always reports to servers, and the people using its data cost little
to add.

The guidance under the choice says what to describe for the selected scope: for Web + edge, the
devices and their hardware, how many are deployed per period and for how long, what runs on each
device, how often
it reaches a server, and the web usages. The AI receives instructions written for that scope. When
the description gives devices deployed together, such as one gateway and 40 sensors per building, the
AI may group them with their counts per building instead of multiplying the totals. The summary's
checklist after generation follows the scope too: for Web + edge it adds the deployments, the
devices per group, the device characteristics and the calls to servers.

Both scopes use the same AI model with the same reasoning effort as today. The Web + edge
instructions are longer, so the disclosure under the description states the indicative cost and
impact of the selected scope; the summary states the estimate of the call actually made.

The design page of today's flow is
[Start a modeling with AI](../../design/journeys/ai-bootstrap.html). The changes, screen by screen:

- **The description panel** (screen 3) reads the scope choice above the description, with **Web only**
  selected. The guidance paragraphs and the disclosure line below the form follow the selected
  scope; changing it keeps what the user typed.
- **The refused generation** (screen 5) shows the error with the description and the scope the
  user had chosen.
- **The summary panel** (screen 6) after a Web + edge generation lists the edge checks after the web ones; the
  canvas shows the edge objects, and Edge modeling is on.

## Rules no screen shows

- **web-by-default** Opening Start with AI selects Web only, whatever was chosen in an earlier
  bootstrap.
- **web-only-stays-web** A Web only generation creates no edge object.
- **edge-scope-builds-edge** A Web + edge description of deployed devices produces a modeling with
  those devices, what runs on them, how many are deployed each period and how long they stay in
  service.
- **groups-when-relevant** Devices described as deployed together, per site or per vehicle, may be
  grouped with their counts per unit; a fleet described by its total alone needs no group. Either
  way, each deployment holds the number of each device the description gives.
- **fleet-as-deployments** A fleet is modeled by its deployments per period and how long each stays
  in service. A fleet already in service is deployed from a start date in the past, so the
  modeling counts it; a fleet size the description states is turned into deployments, and the
  value's comment says how.
- **generated-values-editable** Each generated usage pattern, web or edge, opens in its edit panel
  with the values the AI set, and saving it unchanged keeps them.
- **edge-calls-reach-servers** A device described as sending data to a server is connected to a job
  on that server, and the server appears once whether devices, people or both use it.
- **calls-scale-with-devices** A server receives a device's calls once for every such device
  deployed, whether the devices are grouped or counted as a fleet total.
- **one-request** Each generation makes one request to the AI provider, whatever the scope.
- **scope-disclosed** Before submitting, the user reads the model and the indicative cost and impact
  of the scope selected; the summary states those of the call made.
- **nothing-stored** The scope is not saved with the modeling or kept in the session, like the
  description and the summary.

## Not doing

- An edge-only scope: Web + edge covers a fleet with no web usage.
- Reading the scope from the description, or from the Edge modeling toggle.
- A different AI model or reasoning effort for Web + edge: on the sandbox cases, more reasoning
  brought no gain for a slower, costlier call.
- An installed base: devices already in service are described as deployments over time.
- Deployment timeseries other than the Growth projection inputs.
- Adding edge objects to an existing modeling: bootstrap still starts from an empty one.
- Remembering the scope between bootstraps.
