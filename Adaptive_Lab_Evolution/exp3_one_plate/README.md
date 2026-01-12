# One Plate TFMN1 Experiment Application

an Adaptive Lab Evolution (ALE) Experiment

Science leads: Nidhi Gupta, Paul Hanke, Chris Henry \
Robotics lead: Casey Stone

## Experiment Abstract

This project combines AI hypothesis generation with high-throughput experimental biology to accelerate rational microbial engineering. AI is used to design gene variants for vanillate/vertarate demethylase enzymes in Acinetobacter baylyi. These designs are then tested using automated lab systems and evolving bacterial cultures. Experimental results are fed back into AI models for iterative refinement.

## Experiment Application Details

### Description

This experiment will start with an inoculated microplate with lid (plate 0) at the exchange location. After this initial plate incubates for 12 hours at the start of the experiment, new substrate plates will be inoculated every 12 hours. After inoculation, the new substrate plates will incubate for 12 hours until the next inoculation, with OD(590) absorbance readings every hour. Before inoculating a new substrate plate, we will take an OD(590) reading of the plate to ensure there is no contamination before inoculation.

### Experiment Setup

| Workcell Location | Labware |
| ----------- | ----------- |
| exchange | plate 0 (inoculated microplate with lid) |
| racks (rows 1-4, nests 1-3) | extra substrate microplates with lids |
| ot2_spongebob decks 4-11 | 20uL opentrons tip racks |
| ALL OTHER LOCATIONS | EMPTY |

### Relevant Modules

- Opentrons OT-2 (ot2_spongebob)
- Inheco Single Plate Deepwell Incubator (inheco_irene_2.0)
- BMG Microplate Reader (bmg_billy)
- PF400 Microplate Handler (pf400_piper)












