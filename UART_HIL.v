`timescale 1ns / 1ps

module UART_HIL (
    input clk,          // 100 MHz clock
    input RsRx,         // UART RX (PC -> FPGA)
    output RsTx,        // UART TX (FPGA -> PC)
    input [1:0] sw,     // Switch 0 for 7-Seg Mode
    output [15:0] led,  // The 16 physical LEDs
    output reg [6:0] seg, // 7 segments (A to G)
    output reg [3:0] an   // 4 digit anodes
);

    parameter CLKS_PER_BIT = 10416; // 9600 Baud at 100MHz

    // --- 1. UART RECEIVER ---
    reg [2:0] rx_state = 0;
    reg [13:0] rx_clk_count = 0;
    reg [2:0] rx_bit_index = 0;
    reg [7:0] rx_data = 0;
    reg rx_dv = 0; // Data Valid pulse

    always @(posedge clk) begin
        rx_dv <= 0;
        case (rx_state)
            0: begin rx_clk_count <= 0; rx_bit_index <= 0; if (RsRx == 0) rx_state <= 1; end
            1: begin if (rx_clk_count == (CLKS_PER_BIT / 2)) begin if (RsRx == 0) begin rx_clk_count <= 0; rx_state <= 2; end else rx_state <= 0; end else rx_clk_count <= rx_clk_count + 1; end
            2: begin if (rx_clk_count < CLKS_PER_BIT - 1) rx_clk_count <= rx_clk_count + 1; else begin rx_clk_count <= 0; rx_data[rx_bit_index] <= RsRx; if (rx_bit_index < 7) rx_bit_index <= rx_bit_index + 1; else begin rx_state <= 3; rx_bit_index <= 0; end end end
            3: begin if (rx_clk_count < CLKS_PER_BIT - 1) rx_clk_count <= rx_clk_count + 1; else begin rx_dv <= 1; rx_state <= 0; end end
        endcase
    end

    // --- 2. PACKET PARSER & CONTROL LOGIC ---
    reg [1:0] packet_state = 0;
    reg [7:0] danger_lvl = 0;
    reg [7:0] steering_val = 127;
    
    // Control Outputs
    reg [7:0] brake_out = 0;
    reg [7:0] throttle_out = 0;
    reg trigger_tx = 0; // Tells TX module to send data back

    always @(posedge clk) begin
        trigger_tx <= 0;
        if (rx_dv) begin
            case (packet_state)
                0: if (rx_data == 8'hFF) packet_state <= 1; // Wait for Start Byte (0xFF)
                1: begin danger_lvl <= rx_data; packet_state <= 2; end
                2: begin 
                    steering_val <= rx_data; 
                    packet_state <= 0;
                    
                    // --- AUTONOMOUS CONTROL MATH ---
                    brake_out <= danger_lvl; // Brake scales with danger
                    if (danger_lvl > 50) throttle_out <= 0; // Cut throttle if dangerous
                    else throttle_out <= 100 - (danger_lvl * 2); // Cruise control
                    
                    trigger_tx <= 1; // We have a full packet, send it back!
                end
            endcase
        end
    end

    // --- 3. UART TRANSMITTER ---
    reg [2:0] tx_state = 0;
    reg [13:0] tx_clk_count = 0;
    reg [2:0] tx_bit_index = 0;
    reg [7:0] tx_data_byte = 0;
    reg [2:0] tx_packet_index = 0;
    reg tx_pin_reg = 1;
    assign RsTx = tx_pin_reg;

    always @(posedge clk) begin
        case (tx_state)
            0: begin 
                tx_pin_reg <= 1; 
                if (trigger_tx) begin tx_state <= 1; tx_packet_index <= 0; end 
            end
            1: begin // Load byte to send
                if (tx_packet_index == 0) tx_data_byte <= 8'hFF;
                else if (tx_packet_index == 1) tx_data_byte <= brake_out;
                else if (tx_packet_index == 2) tx_data_byte <= throttle_out;
                else if (tx_packet_index == 3) tx_data_byte <= steering_val;
                else begin tx_state <= 0; tx_packet_index <= 0; end // Done
                
                if (tx_packet_index < 4) begin tx_state <= 2; tx_clk_count <= 0; end
            end
            2: begin tx_pin_reg <= 0; if (tx_clk_count < CLKS_PER_BIT - 1) tx_clk_count <= tx_clk_count + 1; else begin tx_clk_count <= 0; tx_state <= 3; tx_bit_index <= 0; end end // Start bit
            3: begin tx_pin_reg <= tx_data_byte[tx_bit_index]; if (tx_clk_count < CLKS_PER_BIT - 1) tx_clk_count <= tx_clk_count + 1; else begin tx_clk_count <= 0; if (tx_bit_index < 7) tx_bit_index <= tx_bit_index + 1; else tx_state <= 4; end end // Data bits
            4: begin tx_pin_reg <= 1; if (tx_clk_count < CLKS_PER_BIT - 1) tx_clk_count <= tx_clk_count + 1; else begin tx_packet_index <= tx_packet_index + 1; tx_state <= 1; end end // Stop bit
        endcase
    end

    // --- 4. VISUAL FLARE: CLOCKS & TIMERS ---
    reg [25:0] timer = 0;
    always @(posedge clk) timer <= timer + 1;
    wire [1:0] active_digit = timer[19:18];
    wire blink_fast = timer[24]; 
    wire blink_slow = timer[25];

    // --- 5. VISUAL FLARE: LEDs ---
    reg [15:0] led_reg;
    always @(*) begin
        led_reg = 16'b0;
        // Turn Indicators (Flash if steering hard)
        if (steering_val < 100 && blink_slow) led_reg[15] = 1'b1; // Left Turn
        if (steering_val > 150 && blink_slow) led_reg[0] = 1'b1;  // Right Turn
        
        // Brake Bar Graph (Center outwards)
        if (brake_out > 20)  begin led_reg[7] = 1'b1; led_reg[8] = 1'b1; end
        if (brake_out > 60)  begin led_reg[6] = 1'b1; led_reg[9] = 1'b1; end
        if (brake_out > 100) begin led_reg[5] = 1'b1; led_reg[10] = 1'b1; end
        if (brake_out > 150) begin led_reg[4] = 1'b1; led_reg[11] = 1'b1; end
        if (brake_out > 200) begin led_reg[3] = 1'b1; led_reg[12] = 1'b1; end
        
        // Critical Danger Strobe
        if (brake_out > 220 && blink_fast) led_reg[14:1] = 14'h3FFF; 
    end
    assign led = led_reg;

    // --- 6. VISUAL FLARE: 7-SEGMENT DISPLAY ---
    reg [7:0] display_val;
    always @(*) begin
        case(sw)
            2'b00: display_val = danger_lvl;
            2'b01: display_val = steering_val;
            2'b10: display_val = brake_out;
            2'b11: display_val = throttle_out;
        endcase
    end

    wire [3:0] hundreds = display_val / 100;
    wire [3:0] tens     = (display_val % 100) / 10;
    wire [3:0] ones     = display_val % 10;
    
    reg [3:0] current_bcd;
    always @(*) begin
        case(active_digit)
            2'b00: begin an = 4'b1110; current_bcd = ones; end
            2'b01: begin an = 4'b1101; current_bcd = tens; end
            2'b10: begin an = 4'b1011; current_bcd = hundreds; end
            2'b11: begin 
                an = 4'b0111; 
                case(sw)
                    2'b00: current_bcd = 4'ha; // 'd' for Danger
                    2'b01: current_bcd = 4'hb; // 'S' for Steering
                    2'b10: current_bcd = 4'hc; // 'b' for Brake
                    2'b11: current_bcd = 4'hd; // 't' for Throttle
                endcase
            end 
        endcase
    end

    always @(*) begin
        case(current_bcd)
            4'd0 : seg = 7'b1000000;
            4'd1 : seg = 7'b1111001;
            4'd2 : seg = 7'b0100100;
            4'd3 : seg = 7'b0110000;
            4'd4 : seg = 7'b0011001;
            4'd5 : seg = 7'b0010010;
            4'd6 : seg = 7'b0000010;
            4'd7 : seg = 7'b1111000;
            4'd8 : seg = 7'b0000000;
            4'd9 : seg = 7'b0010000;
            4'ha : seg = 7'b0100001; // 'd'
            4'hb : seg = 7'b0010010; // 'S'
            4'hc : seg = 7'b0000011; // 'b'
            4'hd : seg = 7'b0000111; // 't'
            default : seg = 7'b1111111; // Blank
        endcase
    end
endmodule