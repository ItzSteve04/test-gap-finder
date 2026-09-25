# Frontend

This folder contains the web interface for Test Gap Finder.

The frontend is responsible for everything the developer sees and interacts with.

## Responsibilities

The frontend will allow the user to:

- provide a repository for analysis
- start the test-gap analysis process
- see the progress of the analysis
- view identified test gaps
- view generated test cases
- view test pass/fail results
- compare test coverage before and after generated tests
- view potential bugs discovered by generated tests

## Technology

The frontend is being built using Angular as part of the team's JavaScript/MEAN-based frontend development.

## `src/`

The `src` folder contains the actual Angular application source code.

This is where the frontend interface, components, application logic, services, and styling will live.

The majority of frontend development will happen inside this folder.

## `angular.json`

This file contains Angular project configuration.

Angular uses it to control things such as how the project is built, served, tested, and configured.

This file will generally be managed by Angular rather than edited frequently by hand.

## `package.json`

This file defines the JavaScript dependencies and scripts used by the frontend.

It records packages required by the Angular application and commands used to run, build, or test the frontend.
