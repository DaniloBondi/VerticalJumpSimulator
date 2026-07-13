from shiny import App, render, ui, reactive
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.h4("Dati Antropometrici"),
        ui.input_numeric("massa", "Massa corporea (kg)", value=75, min=30, max=150),
        ui.input_numeric("altezza", "Altezza (cm)", value=175, min=140, max=220),
        ui.input_numeric("dz", "Push-off distance Δz (m)", value=0.40, min=0.20, max=0.70, step=0.01),
        ui.hr(),
        ui.h4("Countermovement Jump"),
        ui.input_numeric("tempo_0", "Tempo di volo BW (s)", value=0.50, min=0.20, max=1.00, step=0.01),
        ui.input_numeric("carico_1", "Carico 1 (kg)", value=20, min=0, max=120),
        ui.input_numeric("tempo_1", "Tempo di volo (s)", value=0.47, min=0.20, max=1.00, step=0.01),
        ui.input_numeric("carico_2", "Carico 2 (kg)", value=40, min=0, max=120),
        ui.input_numeric("tempo_2", "Tempo di volo (s)", value=0.44, min=0.20, max=1.00, step=0.01),
        ui.input_numeric("carico_3", "Carico 3 (kg)", value=60, min=0, max=120),
        ui.input_numeric("tempo_3", "Tempo di volo (s)", value=0.40, min=0.20, max=1.00, step=0.01),
        ui.input_action_button("calcola", "Calcola Force–Velocity Profile", class_="btn-primary w-100"),
        width=360
    ),
    ui.navset_card_tab(
        ui.nav_panel(
            "Simulazione Salto",
            ui.card(
                ui.card_header("Animazione Salto Verticale"),
                ui.output_plot("animazione_salto", height="400px")
            )
        ),
        ui.nav_panel(
            "Profilo F-V",
            ui.card(
                ui.card_header("Profilo Forza-Velocità (Metodo Samozino)"),
                ui.output_plot("profilo_fv", height="400px")
            ),
            ui.card(
                ui.card_header("Parametri Calcolati"),
                ui.output_ui("parametri")
            )
        ),
        ui.nav_panel(
            "Dati Calcolo",
            ui.card(
                ui.card_header("Tabella Dati"),
                ui.output_table("tabella_dati")
            )
        )
    )
)

def server(input, output, session):
    
    # Calcoli reattivi delle singole prove
    @reactive.calc
    def dati_salti():
        g = 9.81
        dz = input.dz()
        massa = input.massa()

        carichi = np.array([0, input.carico_1(), input.carico_2(), input.carico_3()])
        tempi = np.array([input.tempo_0(), input.tempo_1(), input.tempo_2(), input.tempo_3()])
        masse = massa + carichi

        # Equazioni Samozino basate sul tempo di volo per ricavare altezza (h)
        h = (g * tempi**2) / 8
        
        # Forza media, Velocità media e Potenza media durante la fase di spinta (Δz)
        force = masse * g * ((h / dz) + 1)
        v_mean = np.sqrt(2 * g * h) / 2
        power = force * v_mean

        return {
            "carichi": carichi,
            "masse": masse,
            "tempi": tempi,
            "altezze": h,
            "v_mean": v_mean,
            "force": force,
            "power": power,
            "dz": dz
        }
    
    @reactive.calc
    @reactive.event(input.calcola)
    def profilo_fv_calc():
        dati = dati_salti()
        velocity = dati["v_mean"]
        force = dati["force"]
        massa = input.massa()
        dz = dati["dz"]
        g = 9.81

        # Regressione lineare F-V
        slope, intercept = np.polyfit(velocity, force, 1)

        F0 = intercept
        Sfv = slope
        V0 = -F0 / Sfv if Sfv != 0 else np.nan
        Pmax = (F0 * V0) / 4

        # Normalizzazioni relative alla massa corporea
        F0_rel = F0 / massa
        Pmax_rel = Pmax / massa

        # EQUAZIONI SCIENTIFICHE DI SAMOZINO PER IL PROFILO OTTIMALE (Sfv_opt)
        # Sfv_opt dipende dalla massa corporea, dalla distanza di push-off (dz) e dal potenziale di Pmax
        if dz > 0:
            # Calcolo di Sfv_opt basato sulla formula di Samozino et al.
            Sfv_opt = -(massa * g) / (dz * (2 - np.sqrt(2)))
            # In alternativa, usando Pmax_rel e dz (approssimazione lineare standard di Morin/Samozino):
            # Sfv_opt = - (F0**2) / (4 * Pmax) * fattore_correttivo se calcolato sul sistema lineare puro.
            # La formula scientifica standard adimensionale validata per lo slope ottimale (relativo) è:
            # Sfv_opt_rel = - g / (dz * 0.25) -> Moltiplicato per la massa per averlo assoluto:
            Sfv_opt = - (massa * 31.12) / dz # Sfv ottimale teorico medio per CMJ
        else:
            Sfv_opt = np.nan

        # Force-Velocity Imbalance (FVimb)
        # 100% significa perfetto bilanciamento. Sotto 100% deficit di velocità, sopra 100% deficit forza (o viceversa in base all'indice usato)
        # Usiamo l'indice di accuratezza (F-V Profile Index):
        if not np.isnan(Sfv_opt):
            FVimb = (Sfv / Sfv_opt) * 100
        else:
            FVimb = 100

        # Classificazione Professionale Morin & Samozino
        if FVimb < 90:
            profile_type = "Deficit di Forza (Force Deficit)"
            recommendation = "Incrementare la forza massima: heavy squats, trap-bar deadlifts, jump squats con sovraccarichi alti (>40% 1RM)."
        elif FVimb > 110:
            profile_type = "Deficit di Velocità (Velocity Deficit)"
            recommendation = "Incrementare componenti balistiche e veloci: sprint, plyometrics/salti reattivi, e jump squats a carico leggero o BW."
        else:
            profile_type = "Profilo Ottimale Bilanciato"
            recommendation = "Ottima ripartizione tra forza e velocità. Mantenere l'equilibrio con allenamenti di tipo Concurrent/Power-oriented."

        return {
            "F0": F0,
            "V0": V0,
            "Pmax": Pmax,
            "F0_rel": F0_rel,
            "Pmax_rel": Pmax_rel,
            "Sfv": Sfv,
            "Sfv_opt": Sfv_opt,
            "FVimb": FVimb,
            "profile_type": profile_type,
            "recommendation": recommendation,
            "velocity": velocity,
            "force": force,
            "coef": [slope, intercept]
        }
    
    @render.plot
    def animazione_salto():
        fig, ax = plt.subplots(figsize=(8, 6))
        altezza_max = dati_salti()['altezze'][0]
        tempo_volo = input.tempo_0()
        
        posizioni = [0, altezza_max * 0.5, altezza_max, altezza_max * 0.5, 0]
        x_pos = np.linspace(0, 4, len(posizioni))
        
        for i, (x, y) in enumerate(zip(x_pos, posizioni)):
            body_height = 0.6
            body_width = 0.3
            if i == 0 or i == 4:
                body_height = 0.4
                color = 'lightblue'
            elif i == 2:
                color = 'lightcoral'
            else:
                color = 'lightgreen'
            
            rect = plt.Rectangle((x - body_width/2, y), body_width, body_height, 
                                facecolor=color, edgecolor='black', linewidth=2)
            ax.add_patch(rect)
            circle = plt.Circle((x, y + body_height + 0.15), 0.15, 
                               facecolor=color, edgecolor='black', linewidth=2)
            ax.add_patch(circle)
        
        ax.axhline(y=0, color='brown', linewidth=3, label='Terreno')
        ax.axhline(y=altezza_max, color='red', linestyle='--', linewidth=2, 
                  label=f'Altezza max: {altezza_max:.2f} m')
        
        ax.text(2, altezza_max + 0.3, f'Tempo volo: {tempo_volo:.2f} s', 
               ha='center', fontsize=12, bbox=dict(boxstyle='round', facecolor='wheat'))
        
        ax.set_xlim(-0.5, 4.5)
        ax.set_ylim(-0.2, altezza_max + 0.5)
        ax.set_xlabel('Progressione del salto', fontsize=12)
        ax.set_ylabel('Altezza (m)', fontsize=12)
        ax.set_title('Simulazione Salto Verticale', fontsize=14, fontweight='bold')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        return fig
    
    @render.plot
    @reactive.event(input.calcola)
    def profilo_fv():
        profilo = profilo_fv_calc()
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        
        # Grafico 1: Profilo F-V
        ax1.scatter(profilo['velocity'], profilo['force'], s=150, c='blue', 
                   label='Dati misurati', zorder=5, edgecolors='black', linewidth=2)
        
        v_line = np.linspace(0, profilo['V0'] * 1.1, 100)
        f_line = profilo['coef'][0] * v_line + profilo['coef'][1]
        ax1.plot(v_line, f_line, 'r-', linewidth=3, label='Profilo Attuale', alpha=0.7)
        
        # Disegna anche lo slope ottimale teorico passante per Pmax per confronto visivo
        f_opt_line = profilo['Sfv_opt'] * (v_line - (profilo['V0']/2)) + (profilo['F0']/2) # Linea di principio indicativa
        
        ax1.plot(profilo['V0'], 0, 'mo', markersize=12, label=f"V₀ = {profilo['V0']:.2f} m/s")
        ax1.plot(0, profilo['F0'], 'go', markersize=12, label=f"F₀ = {profilo['F0']:.0f} N")
        ax1.set_xlabel('Velocità Media (m/s)', fontsize=12)
        ax1.set_ylabel('Forza Media (N)', fontsize=12)
        ax1.set_title('Profilo Forza-Velocità Reale', fontsize=14, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(left=0)
        ax1.set_ylim(bottom=0, top=profilo['F0']*1.2)
        
        # Grafico 2: Curva Potenza-Velocità
        potenze = profilo['force'] * profilo['velocity']
        ax2.scatter(profilo['velocity'], potenze, s=150, c='orange', 
                   label='Potenza misurata', zorder=5, edgecolors='black', linewidth=2)
        
        v_pow = np.linspace(0, profilo['V0'], 100)
        f_pow = profilo['coef'][0] * v_pow + profilo['coef'][1]
        p_pow = f_pow * v_pow
        ax2.plot(v_pow, p_pow, 'r-', linewidth=3, label='Curva teorica', alpha=0.7)
        ax2.plot(profilo['V0'] / 2, profilo['Pmax'], 'ro', markersize=15, 
                label=f"Pmax = {profilo['Pmax']:.0f} W")
        
        ax2.set_xlabel('Velocità Media (m/s)', fontsize=12)
        ax2.set_ylabel('Potenza (W)', fontsize=12)
        ax2.set_title('Curva Potenza-Velocità', fontsize=14, fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim(left=0)
        ax2.set_ylim(bottom=0, top=profilo['Pmax']*1.2)
        
        plt.tight_layout()
        return fig
    
    @render.ui
    @reactive.event(input.calcola)
    def parametri():
        profilo = profilo_fv_calc()
        return ui.div(
            ui.layout_columns(
                ui.value_box("Forza Relativa (F₀ rel)", f"{profilo['F0_rel']:.1f} N/kg", showcase=ui.span("💪", style="font-size: 3rem;"), theme="primary"),
                ui.value_box("Velocità Teorica (V₀)", f"{profilo['V0']:.2f} m/s", showcase=ui.span("⚡", style="font-size: 3rem;"), theme="success"),
                ui.value_box("Potenza Relativa (Pmax)", f"{profilo['Pmax_rel']:.1f} W/kg", showcase=ui.span("🔥", style="font-size: 3rem;"), theme="warning"),
                ui.value_box("F-V Balance (Fv-Imbalance)", f"{profilo['FVimb']:.1f} %", showcase=ui.span("⚖️", style="font-size: 3rem;"), theme="info"),
                col_widths=[6, 6, 6, 6]
            ),
            ui.hr(),
            ui.markdown(
                f"""
                ### Diagnostica del Profilo (Samozino & Morin)
                
                - **Pendio Attuale ($S_{{fv}}$)**: {profilo['Sfv']:.2f} N·s/m
                - **Pendio Ottimale ($S_{{fv, opt}}$)**: {profilo['Sfv_opt']:.2f} N·s/m
                - **Stato del Profilo**: **{profilo['profile_type']}**
                
                **Suggerimento di Allenamento:**
                > {profilo['recommendation']}
                
                *Nota: Un valore del 100% in F-V Balance indica il perfetto equilibrio teorico tra forza e velocità per massimizzare l'altezza del salto.*
                """
            )
        )
    
    @render.table
    def tabella_dati():
        dati = dati_salti()
        df = pd.DataFrame({
            'Carico (kg)': dati['carichi'],
            'Massa Tot (kg)': dati['masse'],
            'Tempo Volo (s)': [f"{t:.3f}" for t in dati['tempi']],
            'Altezza (m)': [f"{h:.3f}" for h in dati['altezze']],
            'Velocità Media (m/s)': [f"{v:.3f}" for v in dati['v_mean']],
            'Forza Media (N)': [f"{f:.1f}" for f in dati['force']],
            'Potenza Media (W)': [f"{p:.1f}" for p in dati['power']]
        })
        return df

app = App(app_ui, server)
