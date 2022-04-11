create:
	singularity build --fakeroot katr.sif katr.def
run:
	./katr.sif
