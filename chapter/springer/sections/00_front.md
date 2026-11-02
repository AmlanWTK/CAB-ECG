# Calibrate, Adapt, or Block: A Statistically Certified Deployment Gate for Imported Sepsis Early-Warning Models

Amlan Sarkar*, Md Tobibul Islam

Department of Biomedical Engineering, Military Institute of Science and Technology, Bangladesh

amlansarkar738@gmail.com, tobibul.islam@bme.mist.ac.bd

## Abstract

Hospitals increasingly deploy sepsis prediction models developed elsewhere, yet performance can change at a new hospital, and point estimates from small local samples can make inadequate models appear acceptable. We present CAB (Calibrate, Adapt, or Block), a deployment gate for imported models. Before examining local labels, the hospital fixes a minimum patient-level sensitivity and a maximum false-alert rate. CAB considers keeping the model, adjusting its alert threshold and adapting it to local data, in that order, deploys the first configuration certified by exact binomial tests, and otherwise blocks it. If the requirements are fixed before labelling, the labelled patients are a random sample of the receiving hospital's patients and their labels are correct, the probability of deploying a configuration violating either requirement is at most a chosen level α, without requiring the developing and receiving hospitals to have the same patient distribution. In a retrospective evaluation on 40,336 ICU patients from two US hospitals (PhysioNet/CinC Challenge 2019), CAB was compared with eleven alternatives across labelled sample sizes of 250 to 12,000 patients. Imported models failed in direction-dependent ways: sensitivity fell to 63% against an 80% target at one hospital, while the proportion of non-septic patients alerted doubled at the other. Six conventional approaches deployed configurations violating the requirements in 77–92% of runs, and point-estimate validation did so in about a third, compared with 0.7% for CAB. CAB's observed rates were consistent with its bound at all three error levels tested. At the primary requirements, CAB blocked the unrepairable model in every run and certified an adapted model in 97% of runs with 12,000 labels. The guarantee concerns the deployment decision, not clinical benefit. Hospitals should plan for possible blocking, define their tolerated false-alert rate, and arrange label collection before deployment.

## Keywords

Sepsis early warning, Dataset shift, Model updating, Local validation, Statistical certification, Clinical decision support
