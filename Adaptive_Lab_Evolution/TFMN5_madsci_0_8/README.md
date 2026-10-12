# Two plate TFMN5 Experiment Application

An Adaptive Lab Evolution (ALE) Experiment

Science leads: Nidhi Gupta, Paul Hanke, Chris Henry \
Robotics lead: Casey Stone

This experiment application is designed to support multiple concurrent instances of the experiment on the RAPID-446 workcell at Argonne National Laboratory.

We have successfully demonstrated two concurrent experiment instances sharing workcell resources and locations for over a month. We plan to scale up to additional concurrent experiments in future runs.

## Experimental Runs

This application was used to generate more than 1,000 CSV files containing absorbance readings from the BMG VANTAstar microplate reader during experiments TFMN5, TFMN6, and TFMN7.

These experiments ran from September 2 through October 8, 2026.

**This is our longest-running ALE experiment to date!**

## Experiment Setup

| Workcell Location | Labware |
| ----------- | ----------- |
| exchange_wide/narrow | plate 0 for experiment set 1: inoculated microplate with lid |
| sciclops_plankton.stack1 | extra substrate microplates with lids for experiment set 1 |
| sciclops_plankton.stack2 | extra substrate microplates with lids for experiment set 2 |
| ot2_spongebob decks 4-11 | 20 µL Opentrons tip racks |
| ot2_patrick decks 4-11 | 20 µL Opentrons tip racks |
| ALL OTHER LOCATIONS | EMPTY |

## Running instructions 

Follow these steps to start and run two concurrent experiment instances on the RAPID-446 workcell.

1. **Set up the labware.** Place all initial labware at the RAPID-446 workcell locations specified in the Experiment Setup section.
2. **Start the required systems.** Start all required MADSci nodes on both the Linux and Windows computers, along with the RAPID-446 lab. Verify that all nodes and lab managers are functioning correctly before proceeding.
3. **Start experiment set 1.** Ensure that plate 0 for experiment set 1 is positioned at the exchange location. Open a terminal and launch the experiment application using the settings file for experiment set 1.
4. **Wait for the first incubation interval.** Allow experiment set 1 to complete its first inoculation and begin the first incubation interval for plate 1.
5. **Prepare experiment set 2.** While plate 1 of experiment set 1 is incubating, place plate 0 for experiment set 2 at the exchange location.
6. **Start experiment set 2.** Open a separate terminal or terminal tab and launch the experiment application again, this time using the settings file for experiment set 2.
7. **Verify concurrent operation.** Both experiment application instances should now be running concurrently.
8. **Restock labware as needed.** Monitor labware supplies throughout the experiment and restock as required. Opentrons tip racks must be restocked at intervals of no more than approximately 80 hours.


## Relevant Modules

Liquid handling
- Opentrons OT-2 (ot2_spongebob)
- Opentrons OT-2 (ot2_patrick)

Incubation
- Inheco Single Plate Deepwell Incubator (inheco_irene_2.0)
- Inheco Single Plate Deepwell Incubator (inheco_iris_2.1)

Measurement
- BMG Microplate Reader (bmg_billy)

Plate handling
- PF400 Microplate Handler (pf400_piper)
- Hudson SciClops Robotic Arm (sciclops_plankton)


