# Experiment 3 

Adaptive Lab Evolution Experimental Application

Science leads: Nidhi Gupta, Paul Hanke, Chris Henry
Robotics lead: Casey Stone

## Experiment Abstract

This project combines AI hypothesis generation with high-throughput experimental biology to accelerate rational microbial engineering. AI is used to design gene variants for vanillate/vertarate demethylase enzymes in Acinetobacter baylyi. These designs are then tested using automated lab systems and evolving bacterial cultures. Experimental results are fed back into AI models for iterative refinement.

## Experiment Application Details

### Description

This experiment will start with an inoculated microplate with lid (plate 0) at the exchange location. After this initial plate incubates for 10 hours at the start of the experiment, new substrate plates will be inoculated every 10 hours. After inoculation, the new substrate plates will incubate for 10 hours until the next inoculation, with OD(590) absorbance readings every hour. Before inoculating a new substrate plate, we will take an OD(590) reading of the plate to ensure there is no contamination before inoculation.

### Experiment Setup 

| Workcell Location | Labware |
| ----------- | ----------- |
| exchange | plate 0 (inoculated microplate with lid) |
| tower decks 1-5 | extra substrate microplates with lids |
| ot2biobeta decks 4-11 | 20uL opentrons tip racks |
| ALL OTHER LOCATIONS | EMPTY |

### Relevant Modules

- Opentrons OT-2 (ot2biobeta)
- Inheco Single Plate Deepwell Incubator (inheco_devID2_floor0)
- BMG Microplate Reader (bio_bmg)
- PF400 Microplate Handler (biopf400)












