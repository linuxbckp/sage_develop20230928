===========================================================================
 Sage: Open Source Mathematics Software: Finding maximum cliques with mcqd
===========================================================================

About SageMath
--------------

   "Creating a Viable Open Source Alternative to
    Magma, Maple, Mathematica, and MATLAB"

   Copyright (C) 2005-2023 The Sage Development Team

   https://www.sagemath.org

SageMath fully supports all major Linux distributions, recent versions of
macOS, and Windows (using Cygwin or Windows Subsystem for Linux).

The traditional and recommended way to install SageMath is from source via
Sage-the-distribution (https://www.sagemath.org/download-source.html).
Sage-the-distribution first builds a large number of open source packages from
source (unless it finds suitable versions installed in the system) and then
installs the Sage Library (sagelib, implemented in Python and Cython).


About this pip-installable source distribution
----------------------------------------------

This pip-installable source distribution ``sagemath-mcqd`` is a small
optional distribution for use with ``sagemath-standard``.

It provides a Cython interface to the ``mcqd`` library,
providing a fast exact algorithm for finding a maximum clique in
an undirected graph.
