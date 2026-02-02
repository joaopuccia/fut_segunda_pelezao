from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

POSICOES = [('GOL','Goleiro'),('ZAG','Zagueiro'),('LAT','Lateral'),('VOL','Volante'),('MEI','Meia'),('ATA','Atacante')]

class InscricaoForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(min=2, max=200)])
    posicao = SelectField('Posição principal', choices=POSICOES, validators=[DataRequired()])
    posicao_secundaria = SelectField('Posição secundária (opcional)', choices=[('','—')] + POSICOES, validators=[Optional()])
    submit = SubmitField('Confirmar presença')
