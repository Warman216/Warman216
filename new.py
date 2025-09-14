from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window
from kivy.uix.modalview import ModalView
from kivy.properties import StringProperty, ListProperty
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle

import math
import cmath
import operator
import ast

# ======================================
# Enhanced Safe Expression Evaluator
# ======================================
class SafeEval(ast.NodeVisitor):
    ALLOWED_NAMES = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
    ALLOWED_NAMES.update({k: getattr(cmath, k) for k in dir(cmath) if not k.startswith("_")})
    ALLOWED_NAMES.update({
        'abs': abs, 'round': round, 'max': max, 'min': min,
        'sum': sum, 'pi': math.pi, 'e': math.e, 'factorial': math.factorial,
        'sqrt': math.sqrt, 'log': math.log, 'log10': math.log10
    })

    ALLOWED_OPERATORS = {
        ast.Add: operator.add, ast.Sub: operator.sub,
        ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.USub: operator.neg,
        ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv
    }

    def __init__(self, mode="rad"):
        self.mode = mode
        self.variables = {}

    def set_mode(self, mode):
        self.mode = mode

    def visit(self, node):
        if isinstance(node, ast.Expression):
            return self.visit(node.body)
        elif isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.BinOp):
            left = self.visit(node.left)
            right = self.visit(node.right)
            if type(node.op) is ast.Div and right == 0:
                raise ZeroDivisionError("Division by zero")
            return self.ALLOWED_OPERATORS[type(node.op)](left, right)
        elif isinstance(node, ast.UnaryOp):
            return self.ALLOWED_OPERATORS[type(node.op)](self.visit(node.operand))
        elif isinstance(node, ast.Call):
            if not hasattr(node.func, 'id') or node.func.id not in self.ALLOWED_NAMES:
                raise ValueError(f"Function {getattr(node.func, 'id', 'unknown')} not allowed")

            func = self.ALLOWED_NAMES[node.func.id]
            args = [self.visit(arg) for arg in node.args]

            if self.mode == "deg" and node.func.id in ["sin", "cos", "tan", "asin", "acos", "atan"]:
                if node.func.id.startswith('a'):
                    result = func(*args)
                    return math.degrees(result) if result is not None else None
                else:
                    args = [math.radians(a) for a in args]
            return func(*args)
        elif isinstance(node, ast.Name):
            if node.id in self.ALLOWED_NAMES:
                return self.ALLOWED_NAMES[node.id]
            elif node.id in self.variables:
                return self.variables[node.id]
            else:
                raise NameError(f"Name '{node.id}' is not defined")
        else:
            raise ValueError("Unsupported operation")

    def eval_expr(self, expr):
        try:
            expr = expr.replace('^', '**').replace('÷', '/').replace('×', '*')
            return self.visit(ast.parse(expr, mode='eval'))
        except Exception as e:
            return f"Error: {str(e)}"


# ======================================
# History Popup for Kivy
# ======================================
class HistoryPopup(ModalView):
    def __init__(self, history, calculator, **kwargs):
        super().__init__(**kwargs)
        self.history = history
        self.calculator = calculator
        self.size_hint = (0.9, 0.9)
        self.background_color = (0.1, 0.1, 0.1, 1)
        self.build_ui()
        
    def build_ui(self):
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        # Title and close button
        title_layout = BoxLayout(size_hint_y=None, height=50)
        title = Label(text="Calculation History", font_size=24, bold=True, color=(1, 1, 1, 1))
        close_btn = Button(text="✕", size_hint=(None, None), size=(50, 50),
                          background_color=(1, 0.4, 0.4, 1))
        close_btn.bind(on_release=self.dismiss)
        
        title_layout.add_widget(title)
        title_layout.add_widget(Label())  # Spacer
        title_layout.add_widget(close_btn)
        layout.add_widget(title_layout)
        
        # Separator
        separator = Label(size_hint_y=None, height=2)
        separator.canvas.before.clear()
        with separator.canvas.before:
            Color(0.3, 0.3, 0.3, 1)
            Rectangle(pos=separator.pos, size=separator.size)
        layout.add_widget(separator)
        
        # Scroll view for history
        scroll = ScrollView()
        self.history_layout = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        self.history_layout.bind(minimum_height=self.history_layout.setter('height'))
        scroll.add_widget(self.history_layout)
        layout.add_widget(scroll)
        
        # Clear button
        clear_btn = Button(text="Clear History", size_hint_y=None, height=60,
                          background_color=(0.6, 0.3, 0.7, 1))
        clear_btn.bind(on_release=self.clear_history)
        layout.add_widget(clear_btn)
        
        self.add_widget(layout)
        self.update_history()
        
    def update_history(self):
        self.history_layout.clear_widgets()
        
        if not self.history:
            no_history = Label(text="No calculation history yet.", font_size=20,
                              color=(0.7, 0.7, 0.7, 1), size_hint_y=None, height=100)
            self.history_layout.add_widget(no_history)
            return
            
        for i, (expr, result) in enumerate(reversed(self.history)):
            history_item = HistoryItem(expr, result, i+1)
            history_item.bind(on_release=lambda instance, expr=expr: self.reuse_entry(expr))
            self.history_layout.add_widget(history_item)
            
    def clear_history(self, instance):
        self.history.clear()
        self.update_history()
        
    def reuse_entry(self, expression):
        self.calculator.current_expression = expression
        self.calculator.display.text = expression
        self.dismiss()


class HistoryItem(Button):
    def __init__(self, expression, result, index, **kwargs):
        super().__init__(**kwargs)
        self.expression = expression
        self.result = result
        self.index = index
        self.size_hint_y = None
        self.height = 80
        self.background_color = (0, 0, 0, 0)  # Transparent background
        self.background_normal = ''
        self.build_ui()
        
    def build_ui(self):
        layout = BoxLayout(orientation='vertical')
        
        # Expression line
        expr_layout = BoxLayout(size_hint_y=None, height=30)
        index_label = Label(text=f"{self.index}.", size_hint_x=None, width=30,
                           color=(0.7, 0.7, 0.7, 1))
        
        expr_text = self.expression
        if len(expr_text) > 30:
            expr_text = expr_text[:27] + "..."
            
        expr_label = Label(text=expr_text, halign='left', text_size=(Window.width - 100, None),
                          color=(1, 1, 1, 1))
        expr_layout.add_widget(index_label)
        expr_layout.add_widget(expr_label)
        layout.add_widget(expr_layout)
        
        # Result line
        result_label = Label(text=f"= {self.result}", halign='left', 
                            text_size=(Window.width - 50, None),
                            color=(0.3, 0.8, 0.8, 1), bold=True,
                            size_hint_y=None, height=30)
        layout.add_widget(result_label)
        
        self.add_widget(layout)
        
        # Add background
        with self.canvas.before:
            Color(0.17, 0.24, 0.31, 1)  # Dark blue-gray
            self.rect = Rectangle(pos=self.pos, size=self.size)
            
        self.bind(pos=self.update_rect, size=self.update_rect)
        
    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


# ======================================
# Calculator Main Layout for Kivy
# ======================================
class CalculatorLayout(BoxLayout):
    current_expression = StringProperty('')
    history = ListProperty([])
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.spacing = 15
        self.padding = 15
        self.calc = SafeEval()
        self.mode = "rad"
        Window.clearcolor = (0.18, 0.18, 0.18, 1)  # Dark background
        self.build_ui()
        
    def build_ui(self):
        # Display
        self.display = TextInput(
            text=self.current_expression, 
            readonly=True,
            font_size=36,
            size_hint_y=None,
            height=100,
            background_color=(0.1, 0.1, 0.1, 1),
            foreground_color=(1, 1, 1, 1),
            padding=20,
            multiline=False
        )
        self.add_widget(self.display)
        
        # Mode indicator and history button
        info_layout = BoxLayout(size_hint_y=None, height=40)
        self.mode_label = Label(text="RAD", color=(0.7, 0.7, 0.7, 1))
        self.history_btn = Button(
            text="History", 
            size_hint=(None, None),
            size=(100, 30),
            background_color=(0.6, 0.3, 0.7, 1)
        )
        self.history_btn.bind(on_release=self.show_history)
        
        info_layout.add_widget(self.mode_label)
        info_layout.add_widget(Label())  # Spacer
        info_layout.add_widget(self.history_btn)
        self.add_widget(info_layout)
        
        # Button grid
        buttons_grid = GridLayout(cols=5, spacing=10, size_hint_y=7)
        
        buttons = [
            ["C", "⌫", "(", ")", "÷"],
            ["7", "8", "9", "×", "sin"],
            ["4", "5", "6", "-", "cos"],
            ["1", "2", "3", "+", "tan"],
            ["0", ".", "±", "=", "√"],
            ["π", "e", "x²", "x³", "mode"]
        ]
        
        # Color categories for buttons
        special_buttons = {"C": (1, 0.4, 0.4, 1), "⌫": (1, 0.4, 0.4, 1)}
        operator_buttons = {"÷": (0.3, 0.8, 0.8, 1), "×": (0.3, 0.8, 0.8, 1), 
                           "-": (0.3, 0.8, 0.8, 1), "+": (0.3, 0.8, 0.8, 1), 
                           "=": (0.3, 0.8, 0.8, 1)}
        function_buttons = {"sin": (0.27, 0.72, 0.82, 1), "cos": (0.27, 0.72, 0.82, 1), 
                           "tan": (0.27, 0.72, 0.82, 1), "√": (0.27, 0.72, 0.82, 1), 
                           "π": (0.27, 0.72, 0.82, 1), "e": (0.27, 0.72, 0.82, 1), 
                           "x²": (0.27, 0.72, 0.82, 1), "x³": (0.27, 0.72, 0.82, 1), 
                           "mode": (0.27, 0.72, 0.82, 1)}
        number_buttons = {"0": (0.33, 0.33, 0.33, 1), "1": (0.33, 0.33, 0.33, 1), 
                         "2": (0.33, 0.33, 0.33, 1), "3": (0.33, 0.33, 0.33, 1), 
                         "4": (0.33, 0.33, 0.33, 1), "5": (0.33, 0.33, 0.33, 1), 
                         "6": (0.33, 0.33, 0.33, 1), "7": (0.33, 0.33, 0.33, 1), 
                         "8": (0.33, 0.33, 0.33, 1), "9": (0.33, 0.33, 0.33, 1), 
                         ".": (0.33, 0.33, 0.33, 1), "(": (0.33, 0.33, 0.33, 1), 
                         ")": (0.33, 0.33, 0.33, 1), "±": (0.33, 0.33, 0.33, 1)}
        
        for row in buttons:
            for label in row:
                btn = Button(text=label, font_size=20)
                
                # Set button colors based on category
                if label in special_buttons:
                    btn.background_color = special_buttons[label]
                elif label in operator_buttons:
                    btn.background_color = operator_buttons[label]
                elif label in function_buttons:
                    btn.background_color = function_buttons[label]
                elif label in number_buttons:
                    btn.background_color = number_buttons[label]
                else:
                    btn.background_color = (0.33, 0.33, 0.33, 1)
                
                btn.bind(on_release=self.on_button_press)
                buttons_grid.add_widget(btn)
                
        self.add_widget(buttons_grid)
        
    def on_button_press(self, instance):
        label = instance.text
        
        if label == "C":
            self.current_expression = ""
        elif label == "⌫":
            self.current_expression = self.current_expression[:-1]
        elif label == "=":
            result = self.calc.eval_expr(self.current_expression)
            self.current_expression = str(result)

            # Only add to history if it's not an error
            if not str(result).startswith("Error:"):
                self.history.append((self.current_expression, result))
            self.animate_display()
        elif label == "mode":
            self.mode = "deg" if self.mode == "rad" else "rad"
            self.calc.set_mode(self.mode)
            self.mode_label.text = self.mode.upper()
            self.current_expression = f"Mode: {self.mode.upper()}"
            self.animate_mode()
        elif label == "±":
            if self.current_expression and self.current_expression[0] == '-':
                self.current_expression = self.current_expression[1:]
            else:
                self.current_expression = '-' + self.current_expression
        elif label == "x²":
            self.current_expression += "**2"
        elif label == "x³":
            self.current_expression += "**3"
        elif label == "√":
            self.current_expression += "sqrt("
        elif label in ["sin", "cos", "tan"]:
            self.current_expression += f"{label}("
        elif label == "π":
            self.current_expression += "pi"
        elif label == "e":
            self.current_expression += "e"
        elif label == "÷":
            self.current_expression += "/"
        elif label == "×":
            self.current_expression += "*"
        else:
            self.current_expression += label
            
        self.display.text = self.current_expression
        
    def on_current_expression(self, instance, value):
        self.display.text = value
        
    def animate_display(self):
        original_color = self.display.background_color
        self.display.background_color = (0.3, 0.8, 0.8, 1)  # Highlight color
        Clock.schedule_once(lambda dt: self.reset_display_color(original_color), 0.2)
        
    def reset_display_color(self, color):
        self.display.background_color = color
        
    def animate_mode(self):
        original_color = self.display.background_color
        self.display.background_color = (0.27, 0.72, 0.82, 1)  # Mode highlight color
        Clock.schedule_once(lambda dt: self.reset_display_color(original_color), 0.3)
        
    def show_history(self, instance):
        popup = HistoryPopup(self.history, self)
        popup.open()
        
    def reuse_history_entry(self, expression):
        self.current_expression = expression


# ======================================
# Kivy App
# ======================================
class CalculatorApp(App):
    def build(self):
        self.title = "Scientific Calculator"
        return CalculatorLayout()


if __name__ == "__main__":
    CalculatorApp().run()