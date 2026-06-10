# VLSI Skills

## Execution mode
Tool-backed through `tools.vlsi_engine.VLSIEngine`.

## Keywords
vlsi, verilog, vhdl, systemverilog, rtl, fpga, asic, hdl, testbench, xilinx, intel fpga, lattice, soc, embedded c, rtos, freertos, zephyr.

## Local capabilities
- Generate Verilog, VHDL, and SystemVerilog HDL modules.
- Generate RTL designs such as adders, counters, FSMs, RAM/ROM, FIFO, ALU, UART, SPI, I2C, PWM, and DSP blocks.
- Generate HDL testbenches.
- Generate FPGA flow scaffolds for supported vendors.
- Generate SoC skeletons and embedded C/C++ peripheral code.
- Generate RTOS examples and assembly routines for supported architectures.

## Required TOM tools
- `vlsi_engine`
- `file_tools` when generated HDL or embedded code must be written to disk

## Routing rule
Use this skill when the task mentions VLSI, HDL, Verilog, VHDL, SystemVerilog, RTL, FPGA, ASIC, testbench generation, SoC design, embedded C peripherals, or RTOS firmware.

## Limitations
- Synthesis, timing closure, place-and-route, board programming, and simulator execution require external EDA tools and hardware-specific constraints.
- Generated HDL must be verified with a simulator and target timing constraints before hardware use.
